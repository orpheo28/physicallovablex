"""Offline photo recording (W27) — not in the live path. Prints key usage before/after, never the key; stops on 402.

    uv run python -m api.cad.photos._record ab                 # A/B: flash vs pro × whoop, vacuum × hero_studio
    uv run python -m api.cad.photos._record one <ref.png> <shot> <category> <out.png> [model]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from api.cad import renders
from api.cad.photos import engine as E
from api.cad.photos import shots as S

ROOT = Path(__file__).resolve().parents[3]
FLASH, PRO = "google/gemini-3.1-flash-image", "google/gemini-3-pro-image"


def usage() -> float:
    from api.fixtures._showcase import key_usage

    return key_usage()


def one(ref: Path | None, shot: str, category: str, out: Path, model: str) -> tuple[float, float]:
    """(seconds, usd) — usd from the key usage delta (OpenRouter updates it within a few seconds)."""
    before = usage()
    t0 = time.monotonic()
    reference = ref.read_bytes() if ref else None
    prompt = S.shot_prompt(shot, category)
    raw = E._generate(prompt, reference, S.SHOTS[shot].aspect_ratio, model, time.monotonic() + 150)
    secs = time.monotonic() - t0
    out.parent.mkdir(parents=True, exist_ok=True)
    E._save(raw, out, S.SHOTS[shot].aspect_ratio)
    cost = renders.last_cost()
    after = usage()
    print(f"  {out.name}: {model} {secs:.1f}s cost ${cost if cost is not None else float('nan'):.4f} "
          f"(key usage ${after:.4f}, delta ${after - before:.4f})", flush=True)
    return secs, cost if cost is not None else after - before


def cmd_ab() -> None:
    pre = ROOT / "api" / "cad" / "prebuilt"
    out = ROOT / "docs" / "screens" / "photos" / "ab"
    cases = [("whoop", pre / "showcase_whoop_kitesurf" / "hero_v4.png", "wearable"),
             ("vacuum", pre / "showcase_stick_vacuum" / "hero_v2.png", "vacuum")]
    for name, ref, cat in cases:
        for tag, model in (("flash", FLASH), ("pro", PRO)):
            one(ref, "hero_studio", cat, out / f"{name}_hero_{tag}.png", model)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["ab"]:
        cmd_ab()
    elif a[:1] == ["one"]:
        one(Path(a[1]) if a[1] != "-" else None, a[2], a[3], Path(a[4]), a[5] if len(a) > 5 else renders.image_model())
    else:
        raise SystemExit(__doc__)
