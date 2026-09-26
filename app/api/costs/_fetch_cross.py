"""One-off fetch of CBP CROSS rulings (precedents) per demo product.

    uv run python api/costs/_fetch_cross.py

The CROSS search API (rulings.cbp.gov/api/search) is the site's own undocumented frontend API: it is called only from this
script, never at runtime or in tests. Output (committed): api/costs/data/cross/<slug>.json = {slug, fetched_on, queries,
rulings[{rulingNumber, subject, rulingDate, tariffs, collection}]}. Stage 11 picks among these cached candidates only.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent / "data" / "cross"
URL = "https://rulings.cbp.gov/api/search"
QUERIES = {
    "desk_lamp": ["rechargeable LED desk lamp", "portable electric lamp battery LED table lamp", "portable lamp China 9903.88.03"],
    "tracker_card": ["bluetooth tracking tag", "bluetooth key finder", "GPS tracker device from China", "bluetooth tag China 9903.88.15", "wireless transmitter China 9903.88.03"],
    "dog_bowl": ["pet feeder", "electronic kitchen scale", "pet food bowl electronic"],
    "keyboard": ["mechanical keyboard", "wireless keyboard USB", "keyboard China 9903.88.15"],
    "espresso_maker": ["portable espresso maker manual", "hand operated coffee maker"],
    "kids_audio": ["children audio player figurine NFC", "toy music player speaker"],
    "smart_ring": ["smart ring sleep tracking", "wearable fitness tracker sensor", "smartwatch China 9903.88.15"],
    "eink_phone": ["smartphone from China", "cellular telephone e-ink display", "mobile phone"],
    "bike_light": ["LED bicycle light", "bicycle lamp rechargeable USB", "bicycle tail light", "bicycle light China 9903.88.03"],
    "air_quality_monitor": ["air quality monitor", "carbon dioxide sensor monitor", "gas detector portable", "sensor China 9903.88.03"],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    with httpx.Client(headers={"User-Agent": "PhysicalLovableX-demo/1.0 (research cache)"}) as c:
        for slug, terms in QUERIES.items():
            seen: dict[str, dict] = {}
            for term in terms:
                r = c.get(URL, params={"term": term, "collection": "ALL", "pageSize": 5, "page": 1, "sortBy": "RELEVANCE"}, timeout=60)
                r.raise_for_status()
                for x in r.json().get("rulings", []):
                    seen.setdefault(x["rulingNumber"], {
                        "rulingNumber": x["rulingNumber"],
                        "subject": x["subject"],
                        "rulingDate": (x.get("rulingDate") or "")[:10],
                        "tariffs": x.get("tariffs") or "",
                        "collection": x.get("collection"),
                        "operationallyRevoked": bool(x.get("operationallyRevoked")),
                        "found_by": term,
                    })
                time.sleep(1)
            (OUT / f"{slug}.json").write_text(json.dumps({"slug": slug, "fetched_on": today, "queries": terms, "rulings": list(seen.values())}, indent=1))
            print(slug, len(seen))


if __name__ == "__main__":
    main()
