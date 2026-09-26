"""One-off fetch of the FCC Part 15 sections cited by the certification map, from the official eCFR versioner API.

    uv run python api/agents/_fetch_ecfr.py

Output (committed): api/agents/data/certs/fcc_part15.json = {fetched_on, source, sections{<n>: {citation, heading, text, url}}}.
Never run at demo time or in tests; certification.py reads the committed file.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent / "data" / "certs" / "fcc_part15.json"
SECTIONS = ["15.19", "15.101", "15.103", "15.107", "15.109", "15.247", "15.407"]
API = "https://www.ecfr.gov/api/versioner/v1/full/{date}/title-47.xml"


def _text(xml: str) -> tuple[str, str]:
    root = ET.fromstring(xml)
    head = re.sub(r"\s+", " ", "".join(root.find(".//HEAD").itertext())).strip() if root.find(".//HEAD") is not None else ""
    body = re.sub(r"\s+", " ", " ".join("".join(p.itertext()) for p in root.iter("P"))).strip()
    return head, body


def main() -> None:
    today = dt.date.today().isoformat()
    sections = {}
    with httpx.Client(headers={"Accept-Encoding": "gzip", "User-Agent": "PhysicalLovableX-demo/1.0 (research cache)"}) as c:
        titles = c.get("https://www.ecfr.gov/api/versioner/v1/titles.json", timeout=60).json()["titles"]
        issue = next(t["latest_issue_date"] for t in titles if t["number"] == 47)  # the versioner only serves dates that have an issue
        time.sleep(1)
        for n in SECTIONS:
            r = c.get(API.format(date=issue), params={"part": 15, "section": n}, timeout=60)
            r.raise_for_status()
            head, body = _text(r.text)
            sections[n] = {
                "citation": f"47 CFR {n}",
                "heading": head,
                "text": body[:600].rsplit(" ", 1)[0] + "…" if len(body) > 600 else body,
                "url": f"https://www.ecfr.gov/current/title-47/section-{n}",
            }
            print(n, head[:70], len(body))
            time.sleep(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"fetched_on": today, "text_as_of": issue, "source": "eCFR versioner API, https://www.ecfr.gov/", "sections": sections}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
