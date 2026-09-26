"""Read side of the committed USITC HTS cache (api/costs/data/hts/, written once by _fetch_hts.py). Offline, no network.

    duty_for(hts, s301_heading=None) -> {code, description, mfn_text, mfn_pct, compound, s301_heading, s301_rate,
                                         source_url, fetched_on} | None

MFN = "general" column of the official schedule; the Section 301 rate is read from the 9903.88.xx heading row
("The duty provided in the applicable subheading + 25%"). Which 9903.88.xx heading applies to a product is NOT in this
cache (it lives in U.S. note 20 lists): it comes from a CBP ruling that cites it, otherwise the caller falls back to an Estimate.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "hts"
S301_FILE = "9903_88"


@lru_cache(maxsize=64)
def _load(name: str) -> dict | None:
    f = DATA / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else None


def digits(code: str) -> str:
    return re.sub(r"\D", "", code or "")


def has_heading(code: str) -> bool:
    return _load(digits(code)[:4]) is not None


def _parse_mfn(text: str) -> tuple[float | None, bool]:
    t = (text or "").strip()
    if not t:
        return None, False
    if t.lower().startswith("free"):
        return 0.0, False
    pcts = re.findall(r"(\d+(?:\.\d+)?)\s*%", t)
    if not pcts:
        return None, False
    compound = bool(re.search(r"[¢$]|/|\+", t)) or len(pcts) > 1
    return float(pcts[0]), compound


def _row_index(rows: list[dict], d: str) -> int | None:
    for i, r in enumerate(rows):
        if digits(r["htsno"]) == d:
            return i
    return None


def _ancestors(rows: list[dict], i: int) -> list[dict]:
    """Parent chain of row i (closest first) using the schedule's indent levels."""
    out, level = [], int(rows[i]["indent"])
    for j in range(i - 1, -1, -1):
        lv_ = int(rows[j]["indent"])
        if lv_ < level:
            out.append(rows[j])
            level = lv_
            if level == 0:
                break
    return out


def _short(t: str, n: int = 70) -> str:
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def lookup(code: str) -> dict | None:
    d = digits(code)
    data = _load(d[:4])
    if not data:
        return None
    rows = data["rows"]
    i = _row_index(rows, d)
    if i is None and len(d) > 8:
        i = _row_index(rows, d[:8])
    if i is None:  # 8-digit ruling code whose only statistical child is the 10-digit row
        kids = [k for k, r in enumerate(rows) if digits(r["htsno"]).startswith(d)]
        i = kids[0] if len(kids) == 1 else None
    if i is None:
        return None
    row, chain = rows[i], _ancestors(rows, i)
    general = row.get("general") or next((a["general"] for a in chain if a.get("general")), "")
    parts = [x["description"] for x in reversed([row, *chain[:1]])]
    desc = " — ".join(_short(re.sub(r"[:;]\s*$", "", p).strip()) for p in parts)
    return {
        "code": row["htsno"], "description": desc, "general": general,
        "fetched_on": data["fetched_on"], "source_url": f"https://hts.usitc.gov/search?query={row['htsno']}",
    }


def s301_for(heading: str | None) -> dict | None:
    """Section 301 additional duty of a 9903.88.xx heading, or None when the heading is unknown / an exclusion (no '+ x%')."""
    if not heading:
        return None
    data = _load(S301_FILE)
    if not data:
        return None
    row = next((r for r in data["rows"] if r["htsno"] == heading), None)
    if row is None:
        return None
    m = re.search(r"(?:\+|plus)\s*(\d+(?:\.\d+)?)\s*%", row.get("general") or "")
    if not m:
        return None
    return {"heading": heading, "rate": float(m.group(1)), "fetched_on": data["fetched_on"], "source_url": f"https://hts.usitc.gov/search?query={heading}"}


def duty_for(hts: str, s301_heading: str | None = None) -> dict | None:
    """MFN rate of the (8- or 10-digit) HTS code + Section 301 rate of `s301_heading`, both from the cached official schedule."""
    r = lookup(hts)
    if r is None:
        return None
    pct, compound = _parse_mfn(r["general"])
    s = s301_for(s301_heading)
    return {
        "code": r["code"], "description": r["description"], "mfn_text": r["general"], "mfn_pct": pct, "compound": compound,
        "s301_heading": s["heading"] if s else None, "s301_rate": s["rate"] if s else None,
        "source_url": r["source_url"], "fetched_on": r["fetched_on"],
    }
