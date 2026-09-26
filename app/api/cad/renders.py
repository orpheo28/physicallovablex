"""AI concept renders for stage 2 — one square studio image per direction. Owner: W12.

    render_direction(project_id, brief, direction, out_dir) -> "/files/<pid>/dN.png" | None

The prompt is built from the brief and the DesignDirection (shape, dimensions, material, finish, colour) so the
image matches the CAD. Model = env LLM_IMAGE_MODEL through OpenRouter (same OpenAI-client config as api/llm.py).
Timeout 25 s, one retry within the caller's deadline, then None — a render never fails stage 2.
The image is illustrative, not the CAD: RENDER_CAPTION is attached as an Assumption (label "estimate").
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from pathlib import Path

from api.llm import _client, _count_request  # also loads .env (OPENROUTER_API_KEY, LLM_IMAGE_MODEL)

log = logging.getLogger("cad.renders")

RENDER_CAPTION = "AI concept render — illustrative, not the CAD"
TIMEOUT_S = 25.0
SIZE = 1024

PROMPT = """Industrial design concept render of a consumer hardware product: {what}.
Design direction "{name}": {description}
Form: {shape}. Overall size {L:.0f} × {W:.0f} × {H:.0f} mm (length × width × height) — keep these proportions exactly.
Construction: two injection-moulded shells meeting at a thin horizontal split line{extra}.
Material: {material}. Finish: {finish}. Colour: {colour}.
Studio product shot, three-quarter view from slightly above, the whole product centred and fully in frame,
seamless light warm-grey background, soft diffused lighting, gentle contact shadow, photorealistic materials.
Product only. No text, no letters, no numbers, no logos, no brand names, no labels, no people, no hands, no props."""


def image_model() -> str | None:
    return os.getenv("LLM_IMAGE_MODEL") or None


def is_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY")) and bool(image_model())


def build_prompt(brief, d, colour_name: str | None = None, extra: str = "") -> str:
    what = getattr(brief, "one_liner", "") or getattr(brief, "product_name", "") or "a small electronic product"
    return PROMPT.format(
        what=what.rstrip("."), name=d.name, description=d.description.rstrip(".") + ".", shape=d.shape,
        L=d.dimensions.length.value, W=d.dimensions.width.value, H=d.dimensions.height.value,
        material=d.material, finish=d.finish, colour=colour_name or "as in the finish", extra=extra,
    )


def _call(prompt: str, timeout: float) -> bytes:
    """One OpenRouter image request → raw image bytes. Raises on any failure."""
    _count_request("image")
    resp = _client().with_options(timeout=timeout).chat.completions.create(
        model=image_model(),
        messages=[{"role": "user", "content": prompt}],
        extra_body={"modalities": ["image", "text"], "image_config": {"aspect_ratio": "1:1"}},
    )
    msg = resp.model_dump()["choices"][0]["message"]
    for img in msg.get("images") or []:
        url = (img.get("image_url") or {}).get("url", "")
        if url.startswith("data:image"):
            return base64.b64decode(url.split(",", 1)[1])
    raise RuntimeError("no image in the response")


def _to_png(raw: bytes, path: Path) -> None:
    from PIL import Image

    im = Image.open(io.BytesIO(raw)).convert("RGB")
    s = min(im.size)  # centre-crop to square, then fit SIZE
    left, top = (im.width - s) // 2, (im.height - s) // 2
    im = im.crop((left, top, left + s, top + s)).resize((SIZE, SIZE), Image.LANCZOS)
    tmp = path.with_suffix(".tmp")
    im.save(tmp, format="PNG", optimize=True)
    tmp.replace(path)


def render(prompt: str, path: Path | str, deadline: float | None = None) -> bool:
    """Generate `prompt` into PNG `path`. 25 s timeout, one retry if time remains before `deadline`."""
    if not is_configured():
        return False
    path = Path(path)
    deadline = deadline or time.monotonic() + 2 * TIMEOUT_S
    for attempt in range(2):
        left = deadline - time.monotonic()
        if left < 3:
            break
        try:
            _to_png(_call(prompt, min(TIMEOUT_S, left)), path)
            return True
        except Exception as e:  # noqa: BLE001 — a missing render is fine, a failed stage is not
            log.warning("render %s attempt %d failed: %s", path.name, attempt + 1, str(e)[:200])
            if getattr(e, "status_code", None) in (401, 402, 403, 429):  # key / credits / rate limit: retrying won't help
                break
    return False


def render_direction(project_id: str, brief, d, out_dir: Path | str, *, colour_name: str | None = None,
                     extra: str = "", deadline: float | None = None) -> str | None:
    """Render direction `d` to <out_dir>/<d.id>.png and return its /files URL, or None."""
    path = Path(out_dir) / f"{d.id}.png"
    ok = render(build_prompt(brief, d, colour_name, extra), path, deadline)
    return f"/files/{project_id}/{d.id}.png" if ok else None


__all__ = ["RENDER_CAPTION", "render", "render_direction", "build_prompt", "is_configured", "image_model"]
