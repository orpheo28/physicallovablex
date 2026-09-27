"""AI concept renders for stage 2 — one square studio image per direction. Owner: W12.

    render_direction(project_id, brief, direction, out_dir) -> "/files/<pid>/dN.png" | None

The prompt is built from the brief and the DesignDirection (shape, dimensions, material, finish, colour) so the
image matches the CAD. Model = env LLM_IMAGE_MODEL through OpenRouter (same OpenAI-client config as api/llm.py).
Timeout 25 s, one retry within the caller's deadline, then None — a render never fails stage 2.
The image is illustrative, not the CAD: RENDER_CAPTION is attached as an Assumption (label "estimate").

W27: this text-only prompt is now the *fallback*. Product photos with a reference image (viewer capture or Blender
render of the CAD) live in api/cad/photos/ (render_product_photo, shot library, listing kit) and reuse `_call`.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import threading
import time
from pathlib import Path

from api.llm import _client, _count_request  # also loads .env (OPENROUTER_API_KEY, LLM_IMAGE_MODEL)

log = logging.getLogger("cad.renders")

RENDER_CAPTION = "AI concept render — illustrative, not the CAD"
TIMEOUT_S = 25.0
SIZE = 1024

PROMPT = """Professional product photograph of a consumer hardware product: {what}.
Design direction "{name}": {description}
Form: {shape}. Overall size {L:.0f} × {W:.0f} × {H:.0f} mm (length × width × height) — keep these proportions exactly.
Construction: {construction}{extra}.
Material: {material}. Finish: {finish}. Colour: {colour}.
Photography: warm paper seamless background (#F4F1EA) curving into the floor, no horizon line. Large soft key light
from camera left at 45°, white bounce fill on the right, subtle rim light separating the top edge from the background.
100 mm macro lens look, three-quarter view from slightly above, the whole product centred with generous negative space,
soft natural contact shadow under it, true-to-life colour, accurate material texture (matte stays matte), crisp edges.
Product only. No text, no letters, no numbers, no logos, no brand names, no labels, no people, no hands, no props."""


def image_model() -> str | None:
    return os.getenv("LLM_IMAGE_MODEL") or None


def is_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY")) and bool(image_model())


SHELLS = "two injection-moulded shells meeting at a thin horizontal split line"


def build_prompt(brief, d, colour_name: str | None = None, extra: str = "", construction: str | None = None) -> str:
    if construction is None:  # W21: a product-family direction (surfboard, drone…) describes its own construction
        from api.cad.family_mode import INFO, family_of

        fam = family_of(d)
        construction = INFO[fam]["desc"].rstrip(".").lower() if fam else SHELLS
    what = getattr(brief, "one_liner", "") or getattr(brief, "product_name", "") or "a small electronic product"
    return PROMPT.format(
        what=what.rstrip("."), name=d.name, description=d.description.rstrip(".") + ".", shape=d.shape,
        L=d.dimensions.length.value, W=d.dimensions.width.value, H=d.dimensions.height.value,
        material=d.material, finish=d.finish, colour=colour_name or "as in the finish", extra=extra,
        construction=construction,
    )


def _call(prompt: str, timeout: float, *, reference: bytes | None = None, aspect_ratio: str = "1:1",
          model: str | None = None) -> bytes:
    """One OpenRouter image request → raw image bytes. Raises on any failure.
    W27: `reference` (PNG/JPEG bytes) is sent as an image part before the prompt — the model edits/restyles it."""
    _count_request("image")
    content: str | list = prompt
    if reference is not None:
        mime = "image/jpeg" if reference[:3] == b"\xff\xd8\xff" else "image/png"
        content = [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(reference).decode()}"}},
                   {"type": "text", "text": prompt}]
    resp = _client().with_options(timeout=timeout).chat.completions.create(
        model=model or image_model(),
        messages=[{"role": "user", "content": content}],
        extra_body={"modalities": ["image", "text"], "image_config": {"aspect_ratio": aspect_ratio},
                    "usage": {"include": True}},
    )
    data = resp.model_dump()
    _last.cost = (data.get("usage") or {}).get("cost")  # OpenRouter usage accounting (USD), for the recording scripts
    msg = data["choices"][0]["message"]
    for img in msg.get("images") or []:
        url = (img.get("image_url") or {}).get("url", "")
        if url.startswith("data:image"):
            return base64.b64decode(url.split(",", 1)[1])
    raise RuntimeError("no image in the response")


_last = threading.local()


def last_cost() -> float | None:
    """USD cost of the last image request on this thread (OpenRouter usage accounting), if reported."""
    return getattr(_last, "cost", None)


def _to_png(raw: bytes, path: Path) -> None:
    from PIL import Image

    im = Image.open(io.BytesIO(raw)).convert("RGB")
    s = min(im.size)  # centre-crop to square, then fit SIZE
    left, top = (im.width - s) // 2, (im.height - s) // 2
    im = im.crop((left, top, left + s, top + s)).resize((SIZE, SIZE), Image.LANCZOS)
    tmp = path.with_suffix(".tmp")
    im.save(tmp, format="PNG", optimize=True)
    tmp.replace(path)


REFERENCE_NOTE = ("The attached image is a capture of the product's 3D model: keep its exact shape, proportions and parts; "
                  "restyle only materials, light and background.\n")


def render(prompt: str, path: Path | str, deadline: float | None = None, reference: bytes | None = None) -> bool:
    """Generate `prompt` into PNG `path`. 25 s timeout, one retry if time remains before `deadline`.
    `reference` (W21d): a viewer capture sent with the prompt (the model restyles it instead of inventing the shape)."""
    if not is_configured():
        return False
    path = Path(path)
    deadline = deadline or time.monotonic() + 2 * TIMEOUT_S
    for attempt in range(2):
        left = deadline - time.monotonic()
        if left < 3:
            break
        try:
            raw = _call(prompt, min(TIMEOUT_S, left), reference=reference) if reference is not None else _call(prompt, min(TIMEOUT_S, left))
            _to_png(raw, path)
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
