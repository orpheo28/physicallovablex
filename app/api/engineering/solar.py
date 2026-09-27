"""Rooftop solar design from cached PVGIS responses (EU JRC PVcalc v5.3). Owner: W20.

    solar_design(text) -> SolarDesign        # location from the prompt (Paris / Biarritz / Tarifa, default Paris)
    solar_checks(design) -> [EngineeringCheck]

Yield per kWp is Sourced (PVGIS, committed cache: data/pvgis/<site>.json, refreshed by _fetch_pvgis.py). Roof area →
module count uses a generic 430 W module and a usable-area share (Estimate); cost and payback are Estimates.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from contracts.artifacts import CheckVerdict, EngineeringCheck, SolarDesign

from api.engineering._util import est, first_number, lv

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
PVGIS_DIR = Path(__file__).resolve().parent / "data" / "pvgis"
LOCATIONS: dict[str, dict] = {
    "paris": {"name": "Paris, France", "lat": 48.8566, "lon": 2.3522, "words": ("paris", "île-de-france", "ile-de-france")},
    "biarritz": {"name": "Biarritz, France", "lat": 43.4832, "lon": -1.5586, "words": ("biarritz", "anglet", "bayonne", "basque")},
    "tarifa": {"name": "Tarifa, Spain", "lat": 36.0143, "lon": -5.6044, "words": ("tarifa", "andalusia", "andalucía", "cadiz", "cádiz")},
}
DEFAULT_SITE = "paris"

MODULE_W = 430.0
MODULE_AREA_M2 = 1.722 * 1.134  # 430 W monocrystalline class, 1722 × 1134 mm
MODULE_KG = 21.5
USABLE_SHARE = 0.75  # setbacks, fire paths, vents, chimney
DEFAULT_ROOF_M2 = 30.0
COST_EUR_PER_WP = 1.9  # residential turnkey (modules, inverter, mounting, install), EU 2026 range 1.5-2.5
EUR_TO_USD = 1.08  # same assumed FX as api/costs/engine.FX_TO_USD
VALUE_EUR_PER_KWH = 0.18  # 60% self-consumed at 0.25 + 40% exported at 0.075
RACKING_KG_M2 = 3.0


@lru_cache(maxsize=8)
def load_pvgis(site: str) -> dict:
    return json.loads((PVGIS_DIR / f"{site}.json").read_text())


def pick_site(text: str) -> tuple[str, bool]:
    low = (text or "").lower()
    for key, loc in LOCATIONS.items():
        if any(w in low for w in loc["words"]):
            return key, False
    return DEFAULT_SITE, True


def _pvgis_source(site: str) -> str:
    d = load_pvgis(site)
    c = d.get("_cache", {})
    return f"PVGIS (EU JRC), fetched {c.get('fetched_on', '?')}, {c.get('url', PVGIS_URL)}"


def solar_design(text: str) -> SolarDesign:
    site, assumed = pick_site(text)
    loc = LOCATIONS[site]
    d = load_pvgis(site)
    src = _pvgis_source(site)
    ey = float(d["outputs"]["totals"]["fixed"]["E_y"])  # kWh per kWp per year
    monthly = [float(m["E_m"]) for m in d["outputs"]["monthly"]["fixed"]]

    area = first_number(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|sq\.? ?m|square met)", text)
    kwp_req = first_number(r"(\d+(?:[.,]\d+)?)\s*kw ?p\b", text)
    if kwp_req:
        count = max(1, math.ceil(kwp_req * 1000 / MODULE_W))
        roof = lv(count * MODULE_AREA_M2 / USABLE_SHARE, "m²", "estimate", f"Roof area needed for {kwp_req:g} kWp requested in the prompt ({count} × {MODULE_AREA_M2:.2f} m² modules / {USABLE_SHARE:.0%} usable)")
        count_note = f"ceil({kwp_req:g} kWp requested / {MODULE_W:.0f} W)"
    else:
        if area:
            roof = lv(area, "m²", "estimate", "Roof area stated in the prompt (not surveyed)")
        else:
            roof = est(DEFAULT_ROOF_M2, "m²", f"Default south-facing roof section {DEFAULT_ROOF_M2:g} m² (no area in the prompt) — survey the roof")
        count = max(1, int(roof.value * USABLE_SHARE // MODULE_AREA_M2))
        count_note = f"floor(roof {roof.value:g} m² × {USABLE_SHARE:.0%} usable / {MODULE_AREA_M2:.2f} m² per module)"
    kwp = count * MODULE_W / 1000
    annual = kwp * ey
    fx = EUR_TO_USD  # W21c: one currency per project — the costing stages are USD, so the solar figures are too
    cost = kwp * 1000 * COST_EUR_PER_WP * fx
    savings = annual * VALUE_EUR_PER_KWH * fx
    pvgis_query = f"{PVGIS_URL}?lat={loc['lat']}&lon={loc['lon']}&peakpower=1&loss=14&angle=30&aspect=0&outputformat=json"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return SolarDesign(
        location=loc["name"], latitude=loc["lat"], longitude=loc["lon"], location_assumed=assumed,
        roof_area=roof,
        module_power=est(MODULE_W, "W", "Generic 430 W monocrystalline module (1722 × 1134 mm class), not a specific product"),
        module_count=est(count, "modules", count_note, nd=0),
        peak_power=est(kwp, "kWp", f"{count} modules × {MODULE_W:.0f} W"),
        specific_yield=lv(ey, "kWh/kWp/yr", "sourced", f"{src} — 30° tilt, due south, 14% system loss", nd=1),
        annual_energy=lv(annual, "kWh/yr", "estimate", f"{kwp:.2f} kWp (Estimate) × {ey:.0f} kWh/kWp/yr (Sourced, PVGIS)", nd=0),
        monthly_energy=[lv(m * kwp, "kWh", "estimate", f"{months[i]}: PVGIS E_m {m:.1f} kWh/kWp (Sourced) × {kwp:.2f} kWp", nd=0) for i, m in enumerate(monthly)],
        install_cost=est(cost, "USD", f"{kwp:.2f} kWp × {COST_EUR_PER_WP} EUR/Wp turnkey residential (EU 2026 range 1.5-2.5 EUR/Wp) × {fx} USD/EUR (assumed FX)", nd=0),
        annual_savings=est(savings, "USD/yr", f"{annual:.0f} kWh/yr × {VALUE_EUR_PER_KWH} EUR/kWh (60% self-consumed at 0.25 + 40% exported at 0.075) × {fx} USD/EUR", nd=0),
        payback=est(cost / savings if savings else 99, "years", f"install cost ${cost:,.0f} / savings ${savings:,.0f}/yr, no subsidy, no tariff inflation", nd=1),
        pvgis_url=pvgis_query,
    )


def solar_checks(s: SolarDesign) -> list[EngineeringCheck]:
    ey, pb = s.specific_yield.value, s.payback.value
    load = s.module_count.value * MODULE_KG / (s.module_count.value * MODULE_AREA_M2) + RACKING_KG_M2
    return [
        EngineeringCheck(
            id="solar_yield", name="Annual energy yield", domain="solar", value=s.annual_energy,
            threshold="Specific yield ≥ 1,000 kWh/kWp/yr pass; ≥ 800 warn",
            verdict=CheckVerdict.pass_ if ey >= 1000 else CheckVerdict.warn if ey >= 800 else CheckVerdict.fail,
            formula="E = kWp × E_y(PVGIS, 1 kWp, 30°, south, 14% loss)", inputs=[s.peak_power, s.specific_yield],
        ),
        EngineeringCheck(
            id="solar_payback", name="Simple payback", domain="solar", value=s.payback,
            threshold="≤ 12 years pass; ≤ 18 warn; else fail",
            verdict=CheckVerdict.pass_ if pb <= 12 else CheckVerdict.warn if pb <= 18 else CheckVerdict.fail,
            formula="payback = install cost / (annual kWh × blended EUR/kWh × FX)", inputs=[s.install_cost, s.annual_savings],
        ),
        EngineeringCheck(
            id="solar_roof_load", name="Added dead load on the roof", domain="stability",
            value=est(load, "kg/m²", f"module {MODULE_KG} kg / {MODULE_AREA_M2:.2f} m² + racking {RACKING_KG_M2} kg/m²", nd=1),
            threshold="≤ 20 kg/m² typical allowance — structural engineer to confirm",
            verdict=CheckVerdict.pass_ if load <= 20 else CheckVerdict.warn,
            formula="q = module mass / module area + racking", inputs=[s.module_power],
            notes=["Check wind uplift and snow load per Eurocode EN 1991-1-4 / 1991-1-3 with the installer"],
        ),
    ]
