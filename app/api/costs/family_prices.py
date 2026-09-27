"""Category price estimates for solid products (W21): surfboard, furniture, rooftop PV.

The geometry costing of api/costs/engine.py (moulded shell, CNC from billet, extrusion) is right for enclosures and
wrong for these: a plywood panel is cut from sheet, a surfboard starts from a foam blank, a PV array is bought-in kit.
When a BOM line has no price, `estimate(family, text, qty)` returns a per-unit Estimate from typical 2026 trade prices
(stated as assumptions, never quotes), else None (the engine's placeholder applies).
"""

from __future__ import annotations

import re

# family -> [(regex on the BOM line, USD per BOM unit, what the price stands for)] — first match wins
TABLE: dict[str, list[tuple[str, float, str]]] = {
    "board": [
        (r"blank|foam|core|stringer", 60.0, "PU / EPS surfboard blank, 7-9 ft"),
        (r"fib(re|er) ?glass|cloth|laminat|resin|epoxy|glassing", 38.0, "fibreglass cloth + laminating / hot-coat resin per board"),
        (r"fin ?box|fin plug|plug", 4.0, "fin box / plug"),
        (r"\bfins?\b", 6.0, "moulded fin"),
        (r"leash", 2.5, "leash plug"),
        (r"traction|deck ?pad|\bpad\b|grip", 12.0, "EVA traction pad"),
        (r"shaping|labou?r|sanding", 25.0, "hand shaping / sanding labour share"),
        (r"sock|bag|carton|box|packag|wrap", 8.0, "board sock / carton"),
    ],
    "furniture": [
        (r"fastener|screw|\bcam\b|dowel|hardware|fitting|bolt|hinge", 4.0, "fitting kit"),
        (r"basket|storage|bin|drawer", 9.0, "fabric / wicker storage basket"),
        (r"pad|mattress|cushion|topper", 15.0, "wipe-clean changing pad"),
        (r"plywood|panel|board|\bleg|guard|rail|shelf|top\b|frame|side", 22.0, "CNC-cut birch plywood part(s) from 2440 × 1220 mm sheet (≈ $55 per 18 mm sheet, nested)"),
        (r"lacquer|paint|finish|oil|varnish", 3.0, "water-based finish per unit"),
        (r"strap|anti-?tip|wall", 1.5, "anti-tip wall strap"),
        (r"instruction|manual|leaflet", 0.4, "printed instructions"),
        (r"carton|packag|box|corner|foam", 7.0, "flat-pack carton + protection"),
    ],
    "solar_array": [  # small parts first: "Module end clamps" is a clamp, "PV DC cable" a cable
        (r"clamp", 1.5, "module clamp"),
        (r"splice|connector|mc4|coupler", 2.5, "connector / splice"),
        (r"cable|wire|conductor|earth|bond|ground|clip|conduit", 1.2, "PV cable / earthing / clips, per metre or piece"),
        (r"hook|anchor|bracket", 4.5, "roof hook"),
        (r"fastener|screw|bolt|nut", 20.0, "stainless fastener set"),
        (r"packag|carton|pallet", 60.0, "packaging and delivery protection per installation"),
        (r"rail", 25.0, "aluminium mounting rail ≈ 4 m"),
        (r"isolator|disconnect", 40.0, "DC isolator"),
        (r"breaker|rcd|residual|protection|surge|spd", 60.0, "AC protection device"),
        (r"monitor|meter|gateway|logger", 120.0, "monitoring gateway / energy meter"),
        (r"(battery|hybrid).{0,25}inverter|inverter.{0,25}(charger|battery)", 950.0, "battery / hybrid inverter-charger"),
        (r"inverter", 850.0, "5-6 kW single-phase string inverter"),
        (r"batter|storage|kwh", 3400.0, "home battery ≈ 10 kWh (LFP), installed-equipment price"),
        (r"module|panel|pv\b|photovoltaic", 110.0, "430-450 W monocrystalline module"),
    ],
}


def estimate(family: str | None, text: str, qty: float = 1.0) -> tuple[float, str] | None:
    for rx, usd, what in TABLE.get(family or "", []):
        if re.search(rx, text or "", re.I):
            return usd, f"Category price estimate: {what} ≈ USD {usd:g} (typical 2026 trade price, not a quote)"
    return None


__all__ = ["estimate", "TABLE"]
