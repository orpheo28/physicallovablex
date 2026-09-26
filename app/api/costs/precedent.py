"""Closest CBP CROSS ruling (precedent) for a product, from the committed cache in api/costs/data/cross/ (written once by
_fetch_cross.py; the undocumented CROSS API is never called at runtime).

    find_precedent(example, text) -> Precedent | None

Deterministic pick among the cached candidates: the ruling must sit in an admissible heading for the product family, be a
classification ruling with a code found in the cached HTS schedule, and score on subject words, China origin, a cited
Section 301 heading (9903.88.xx) and recency. No candidate above the threshold -> None (caller keeps its Estimate).
A precedent is an *assumed* classification, never a binding one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import hts as hts_cache

CROSS_DIR = Path(__file__).resolve().parent / "data" / "cross"

# slug -> (product words in the brief, admissible HTS headings, words expected in a matching ruling subject). Order = priority.
PRODUCTS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "bike_light": (r"bike|bicycle|cycling", ("8512", "8513", "9405"), ("bicycle", "bike", "light", "lamp", "led", "signal")),
    "dog_bowl": (r"\bdog\b|\bpet\b|\bbowl\b|feeder", ("8509", "8423", "3924", "8543"), ("pet", "feeder", "food", "dispenser", "scale")),
    "tracker_card": (r"tracker|\btag\b|finder|airtag|wallet", ("8517", "8526", "8543"), ("tag", "tracker", "tracking", "bluetooth", "pet", "locator")),
    "smart_ring": (r"\bring\b|wearable|smart ?watch|sleep", ("9031", "8517", "9102"), ("ring", "smart", "wearable", "watch", "fitness", "tracker")),
    "keyboard": (r"keyboard", ("8471", "8517"), ("keyboard", "bluetooth", "wireless", "usb")),
    "espresso_maker": (r"espresso|coffee|kettle", ("8516", "8419", "8210", "7323"), ("coffee", "espresso", "maker", "brewer", "press")),
    "kids_audio": (r"audio|speaker|\bnfc\b|music|figurine", ("8518", "8519", "9503", "8523"), ("audio", "music", "player", "speaker", "toy", "mp3")),
    "eink_phone": (r"phone|e-?ink|e-?paper", ("8517",), ("phone", "smartphone", "cellular", "telephone", "mobile")),
    "air_quality_monitor": (r"air[- ]quality|co2|carbon dioxide|sensor|monitor", ("9027", "9025", "9031", "9032"), ("air", "quality", "monitor", "gas", "sensor", "detector", "carbon")),
    "desk_lamp": (r"lamp|flashlight|lantern|light", ("9405", "8513", "8512"), ("lamp", "light", "led", "table", "portable", "desk")),
}
MIN_SCORE = 3.0


@dataclass(frozen=True)
class Precedent:
    slug: str
    ruling: str
    ruling_date: str
    subject: str
    hts: str  # code as cited by the ruling (8-10 digits)
    s301_heading: str | None  # 9903.88.xx heading whose rate is known, cited by `s301_ruling`
    s301_ruling: str | None
    s301_ruling_date: str | None
    fetched_on: str
    url: str

    @property
    def label(self) -> str:
        return f"CBP ruling {self.ruling} ({self.ruling_date})"


def slug_for(example: str | None, text: str) -> str | None:
    if example in PRODUCTS:
        return example
    low = (text or "").lower()
    return next((s for s, (pat, _, _) in PRODUCTS.items() if re.search(pat, low)), None)


@lru_cache(maxsize=32)
def _candidates(slug: str) -> tuple[dict, ...]:
    f = CROSS_DIR / f"{slug}.json"
    if not f.exists():
        return ()
    d = json.loads(f.read_text())
    return tuple({**r, "fetched_on": d["fetched_on"]} for r in d["rulings"])


def _codes(tariffs: str) -> list[str]:
    return [t.strip() for t in re.split(r"[,;]", tariffs or "") if t.strip()]


def _score(slug: str, r: dict, hts_code: str, s301: str | None) -> float:
    words = PRODUCTS[slug][2]
    subj = r["subject"].lower()
    hits = sum(1 for w in words if w in subj)
    score = 1.5 * hits + (1.0 if words[0] in subj else 0.0)  # first word = the product itself
    score += 2.0 if "china" in subj else 0.0
    score += 1.0 if s301 else 0.0
    year = int(r["rulingDate"][:4] or 0)
    score += max(0, year - 2000) / 50  # newer rulings first, tie-break sized
    return score


def _full(code: str) -> str:
    row = hts_cache.lookup(code)
    return hts_cache.digits(row["code"]) if row else hts_cache.digits(code)


def _admissible(slug: str, any_heading: bool = False) -> list[tuple[dict, str, str | None]]:
    """(ruling, main HTS code found in the cached schedule, cited Section 301 heading with a known rate) per usable candidate."""
    headings = PRODUCTS[slug][1]
    out = []
    for r in _candidates(slug):
        subj = r["subject"].lower()
        if "classification" not in subj or "country of origin" in subj or r.get("operationallyRevoked"):
            continue
        codes = _codes(r["tariffs"])
        main = next((c for c in codes if (any_heading or hts_cache.digits(c)[:4] in headings) and hts_cache.lookup(c)), None)
        if main is not None:
            out.append((r, main, next((c for c in codes if c.startswith("9903.88.") and hts_cache.s301_for(c)), None)))
    return out


def find_precedent(example: str | None, text: str) -> Precedent | None:
    slug = slug_for(example, text)
    if slug is None:
        return None
    cands = _admissible(slug)
    scored = [(_score(slug, r, main, s301), r, main, s301) for r, main, s301 in cands]
    if not scored:
        return None
    sc, r, main, s301 = max(scored, key=lambda x: x[0])
    if sc < MIN_SCORE:
        return None
    s_r = s_h = s_d = None
    if s301:
        s_r, s_h, s_d = r["rulingNumber"], s301, r["rulingDate"]
    else:  # same 10-digit HTS code cited with a Section 301 heading in another cached ruling (any product): newest = evidence
        full = _full(main)
        sib = [(rr, h) for sl in PRODUCTS for rr, m, h in _admissible(sl, any_heading=True) if h and _full(m) == full]
        if sib:
            rr, h = max(sib, key=lambda x: x[0]["rulingDate"])
            s_r, s_h, s_d = rr["rulingNumber"], h, rr["rulingDate"]
    return Precedent(slug, r["rulingNumber"], r["rulingDate"], r["subject"], main, s_h, s_r, s_d, r["fetched_on"], f"https://rulings.cbp.gov/ruling/{r['rulingNumber']}")
