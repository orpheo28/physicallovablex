"""Category packs (packs/*.json) and category detection. Owner: W20.

    load_pack(key) -> dict ; pack_keys() -> [key] ; detect_category(text, brief_category, family) -> key
    standards_for(pack) -> [StandardRef]   # citation Sourced only when the URL was checked to load (packs/_standards.json)

A pack = applicable standards, key design risks, required tests, which physics checks apply, their parameters
(thresholds, duty cycles, defaults) and the prototype route. Adding a category = adding one JSON file.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from contracts.artifacts import DesignRisk, Label, RequiredTest, StandardRef

PACKS_DIR = Path(__file__).resolve().parent / "packs"
# Detection order: the first pack whose words match wins (specific before broad: a "kitesurf wearable" is a wearable,
# a "solar-powered irrigation valve" is irrigation, a "desk lamp" is lighting before furniture).
ORDER = ["solar_roof", "irrigation", "vacuum", "drone", "smartphone", "hair_dryer", "home_robot", "wearable", "surfboard",
         "furniture_baby", "camera", "lighting", "tracker"]
FALLBACK = "generic"


def pack_keys() -> list[str]:
    return sorted(p.stem for p in PACKS_DIR.glob("*.json") if not p.stem.startswith("_"))


@lru_cache(maxsize=32)
def load_pack(key: str) -> dict:
    path = PACKS_DIR / f"{key}.json"
    if not path.exists():
        path = PACKS_DIR / f"{FALLBACK}.json"
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def standards_registry() -> dict[str, dict]:
    return json.loads((PACKS_DIR / "_standards.json").read_text())["standards"]


def _hit(words: list[str], text: str) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text) for w in words)


def detect_category(text: str, brief_category: str | None = None, family: str | None = None) -> str:
    """Pack key from the product text (prompt, name, one-liner, features), the brief category and the Studio shape family."""
    low = (text or "").lower()
    if "solar" in low and "irrigation" not in low and _hit(["roof", "rooftop", "array", "kwp", "install", "panels", "house", "home"], low):
        return "solar_roof"
    for key in ORDER:
        if _hit(load_pack(key)["match"], low):
            return key
    for key in ORDER:
        pack = load_pack(key)
        if family and family in pack.get("families", []):
            return key
        if brief_category and brief_category in pack.get("brief_categories", []):
            return key
    return FALLBACK


def standards_for(pack: dict) -> list[StandardRef]:
    reg = standards_registry()
    out = []
    for s in pack["standards"]:
        meta = reg.get(s["code"], {})
        if meta.get("url") and meta.get("verified_on"):
            label, note = Label.sourced, f"{meta['url']}, page checked {meta['verified_on']}"
        else:
            label, note = Label.estimate, "Standard to be confirmed (edition and applicability) — no verified citation URL"
        out.append(StandardRef(code=s["code"], title=meta.get("title", s["code"]), applies_because=s["applies_because"],
                               url=meta.get("url") if label == Label.sourced else None, citation_label=label, citation_note=note))
    return out


def risks_for(pack: dict) -> list[DesignRisk]:
    return [DesignRisk(id=f"r{i + 1}", risk=r["risk"], mitigation=r["mitigation"], severity=r.get("severity", "major"))
            for i, r in enumerate(pack["risks"])]


def tests_for(pack: dict) -> list[RequiredTest]:
    return [RequiredTest(id=f"t{i + 1}", name=t["name"], kind=t["kind"], method=t["method"], standard=t.get("standard"))
            for i, t in enumerate(pack["tests"])]
