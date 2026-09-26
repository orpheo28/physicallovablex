"""Model-agnostic LLM client (OpenAI SDK → OpenRouter). Owner: W0.

One entry point for every agent:

    from api.llm import complete_json, LLMError
    brief = complete_json("main", prompt, BriefDraft)          # returns a validated BriefDraft

- Three routes from env (never hard-coded): main (reasoning), fast (planners, factory agents), cn (Chinese).
- The schema is sent in the prompt AND as response_format when the model supports it; the reply is always
  validated with Pydantic. On invalid output: 1 retry with the validation error appended, then `LLMError`.
- Stage handlers let `LLMError` propagate: the stage runner catches it and serves the fixture (fallback: true).
- Cost guard: LLM_MAX_TOKENS per request, LLM_MAX_REQUESTS per process.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Literal, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

log = logging.getLogger("llm")

Route = Literal["main", "fast", "cn"]
T = TypeVar("T", bound=BaseModel)

ROUTE_ENV: dict[str, str] = {"main": "LLM_MAIN_MODEL", "fast": "LLM_FAST_MODEL", "cn": "LLM_CN_MODEL"}
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class LLMError(Exception):
    """Any LLM failure. The stage runner catches it (and every other exception) and falls back to fixtures."""

    def __init__(self, route: str, reason: str, raw: str | None = None):
        super().__init__(f"[{route}] {reason}")
        self.route = route
        self.reason = reason
        self.raw = raw


class LLMNotConfigured(LLMError):
    pass


class LLMBudgetExceeded(LLMError):
    pass


class LLMValidationError(LLMError):
    pass


_lock = threading.Lock()
_request_count = 0


def model_for(route: Route) -> str | None:
    return os.getenv(ROUTE_ENV[route]) or None


def is_configured(route: Route = "main") -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY")) and bool(model_for(route))


def configured_models() -> dict[str, str | None]:
    return {r: model_for(r) for r in ROUTE_ENV}  # type: ignore[arg-type]


def _client(timeout_s: float | None = None):
    from openai import OpenAI

    return OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
        api_key=os.environ["OPENROUTER_API_KEY"],
        timeout=min(timeout_s or 1e9, float(os.getenv("LLM_TIMEOUT_S", "60"))),
        max_retries=0,
    )


def _count_request(route: str) -> None:
    global _request_count
    limit = int(os.getenv("LLM_MAX_REQUESTS", "500"))
    with _lock:
        if _request_count >= limit:
            raise LLMBudgetExceeded(route, f"request cap reached ({limit})")
        _request_count += 1


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(text: str) -> str:
    text = _FENCE.sub("", text.strip()).strip()
    if text.startswith("{") or text.startswith("["):
        return text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _reasoning() -> dict:
    """OpenRouter unified reasoning control (ignored by models without reasoning). LLM_REASONING_EFFORT=none|minimal|low|
    medium|high; default 'low' keeps structured stages fast and stops reasoning from eating the max_tokens budget."""
    effort = os.getenv("LLM_REASONING_EFFORT", "low").strip().lower()
    return {} if effort in ("", "default", "off") else {"extra_body": {"reasoning": {"effort": effort}}}


def _call(route: Route, model: str, messages: list[dict], schema: type[BaseModel], max_tokens: int, temperature: float,
          timeout_s: float | None = None) -> str:
    _count_request(route)
    client = _client(timeout_s)
    started = time.monotonic()
    kwargs = dict(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **_reasoning())
    try:
        resp = client.chat.completions.create(
            **kwargs,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": False},
            },
        )
    except Exception as e:  # some models/providers reject json_schema → plain JSON mode
        if "timeout" in type(e).__name__.lower() or "timed out" in str(e).lower():
            raise LLMError(route, f"request timed out: {e}") from e  # retrying in another mode would only double the wait
        if getattr(e, "status_code", None) in (401, 402, 403, 429):  # auth / credits / rate limit: not a format problem
            raise LLMError(route, f"request failed: {e}") from e
        log.info("json_schema response_format rejected by %s (%s); retrying with json_object", model, e)
        try:
            resp = client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
        except Exception as e2:
            raise LLMError(route, f"request failed: {e2}") from e2
    content = resp.choices[0].message.content if resp.choices else None
    finish = resp.choices[0].finish_reason if resp.choices else None
    usage = getattr(resp, "usage", None)
    log.info("llm %s %s %.1fs finish=%s tokens=%s", route, model, time.monotonic() - started, finish,
             getattr(usage, "completion_tokens", "?"))
    if not content:
        raise LLMError(route, f"empty completion (finish_reason={finish}, max_tokens={max_tokens})")
    return content


def complete_json(
    route: Route,
    prompt: str,
    schema: type[T],
    *,
    system: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.2,
    timeout_s: float | None = None,
) -> T:
    """Call the model on `route` and return an instance of `schema`. Raises LLMError subclasses."""
    model = model_for(route)
    if not os.getenv("OPENROUTER_API_KEY") or not model:
        raise LLMNotConfigured(route, "OPENROUTER_API_KEY or model env var missing")
    max_tokens = min(max_tokens or 4000, int(os.getenv("LLM_MAX_TOKENS", "8000")))

    sys_msg = (system or "You are a precise hardware product engineer.") + (
        "\nReply with ONE JSON object only, no prose, no code fences. It must validate against this JSON Schema:\n"
        + json.dumps(schema.model_json_schema())
    )
    messages: list[dict] = [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]

    last_err: Exception | None = None
    raw = ""
    for attempt in range(2):  # first try + 1 retry
        try:
            raw = _call(route, model, messages, schema, max_tokens, temperature, timeout_s)
        except LLMError as e:
            # reasoning models can spend the whole budget thinking → one retry with a larger budget (still capped)
            if attempt or "empty completion" not in e.reason:
                raise
            max_tokens = min(max_tokens * 2, int(os.getenv("LLM_MAX_TOKENS", "8000")))
            last_err = e
            log.warning("LLM empty completion on %s; retrying with max_tokens=%d", route, max_tokens)
            continue
        try:
            return schema.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError) as e:
            last_err = e
            log.warning("LLM output invalid on %s (attempt %d): %s", route, attempt + 1, str(e)[:300])
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"Your JSON did not validate:\n{str(e)[:2000]}\nReturn the corrected JSON object only."},
            ]
    raise LLMValidationError(route, f"invalid JSON after retry: {str(last_err)[:500]}", raw=raw)


def complete_text(route: Route, prompt: str, *, system: str | None = None, max_tokens: int | None = None) -> str:
    """Free-text helper (e.g. CN translation). Same guards, no schema."""
    model = model_for(route)
    if not os.getenv("OPENROUTER_API_KEY") or not model:
        raise LLMNotConfigured(route, "OPENROUTER_API_KEY or model env var missing")
    _count_request(route)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    try:
        resp = _client().chat.completions.create(
            model=model, messages=messages, max_tokens=min(max_tokens or 2000, int(os.getenv("LLM_MAX_TOKENS", "8000"))),
            **_reasoning(),
        )
    except Exception as e:
        raise LLMError(route, f"request failed: {e}") from e
    content = resp.choices[0].message.content if resp.choices else None
    if not content:
        raise LLMError(route, "empty completion")
    return content
