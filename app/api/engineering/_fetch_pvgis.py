"""Refresh the committed PVGIS cache (EU JRC PVcalc v5.3) for the demo locations. Owner: W20.

    uv run python -m api.engineering._fetch_pvgis

One response per location, normalised to 1 kWp (yield scales linearly with peak power), 14 % system loss,
30° tilt, due south (aspect 0). The engine scales E_y / E_m by the array's kWp and labels the result
Sourced "PVGIS (EU JRC), fetched <date>".
"""

from __future__ import annotations

import json
from datetime import date

import httpx

from api.engineering.solar import LOCATIONS, PVGIS_DIR, PVGIS_URL

PARAMS = {"peakpower": 1, "loss": 14, "angle": 30, "aspect": 0, "outputformat": "json"}


def main() -> None:
    PVGIS_DIR.mkdir(parents=True, exist_ok=True)
    for key, loc in LOCATIONS.items():
        params = {"lat": loc["lat"], "lon": loc["lon"], **PARAMS}
        r = httpx.get(PVGIS_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        data["_cache"] = {"fetched_on": date.today().isoformat(), "url": str(r.url), "location": loc["name"]}
        (PVGIS_DIR / f"{key}.json").write_text(json.dumps(data, indent=1) + "\n")
        print(key, data["outputs"]["totals"]["fixed"]["E_y"], "kWh/kWp/yr")


if __name__ == "__main__":
    main()
