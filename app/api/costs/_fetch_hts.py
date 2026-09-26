"""One-off fetch of the HTS headings the demo needs from the official USITC REST API (never the full schedule).

    uv run python api/costs/_fetch_hts.py

Output (committed): api/costs/data/hts/<heading>.json and 9903_88.json, each {fetched_on, source_url, rows}.
Never run at demo time or in tests; `duty_for` in hts.py reads these files.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent / "data" / "hts"
BASE = "https://hts.usitc.gov/reststop/exportList"
# lamps, trackers/telecom, audio, keyboards/computers, coffee makers, scales/bowls, rings/wearables, bike light, sensors,
# toys, e-ink/other electrical, batteries, sheet-metal/plastics household articles
HEADINGS = [
    "9405", "8513", "8512", "8517", "8518", "8519", "8471", "8516", "8419", "8423", "3924", "9102", "9027",
    "9503", "8543", "8507", "8523", "8528", "7323", "3926", "9031", "9025", "9032", "8509", "8210", "8526",
]


def _fetch(client: httpx.Client, frm: str, to: str) -> tuple[list[dict], str]:
    url = f"{BASE}?from={frm}&to={to}&format=JSON&styles=false"
    r = client.get(url, timeout=60)
    r.raise_for_status()
    return r.json(), url


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    with httpx.Client(headers={"User-Agent": "PhysicalLovableX-demo/1.0 (research cache)"}) as c:
        for h in HEADINGS:
            rows, url = _fetch(c, h, str(int(h) + 1))
            rows = [r for r in rows if str(r.get("htsno", "")).replace(".", "").startswith(h)]
            (OUT / f"{h}.json").write_text(json.dumps({"fetched_on": today, "source_url": url, "rows": rows}, indent=1))
            print(h, len(rows))
            time.sleep(1)
        rows, url = _fetch(c, "9903.88.01", "9903.88.70")
        (OUT / "9903_88.json").write_text(json.dumps({"fetched_on": today, "source_url": url, "rows": rows}, indent=1))
        print("9903.88", len(rows))


if __name__ == "__main__":
    main()
