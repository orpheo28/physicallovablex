"""Sea freight benchmark from the committed Drewry World Container Index snapshot (data/freight_wci.json).

Lane rate (USD per 40ft) is Sourced (URL + assessment date). Everything derived from it is an Estimate:
- FCL: whole containers (40ft = lane rate, 67 m³; 20ft = 0.55 × lane rate, 33 m³); the cheaper of the two, run volume ÷ packed unit volume.
- LCL: lane rate ÷ 67 m³ × consolidation premium (1.5, typical 1.3-2.0×) per m³, minimum charge 1 m³ per shipment.
The cheaper of LCL and FCL is chosen automatically. Air / express have no public benchmark here and stay Fictional (landed.FREIGHT).
"""

from __future__ import annotations

import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

WCI_FILE = Path(__file__).resolve().parent / "data" / "freight_wci.json"
FEU_USABLE_M3 = 67.0  # ~ usable volume of a 40ft container (assumption)
PACK_VOLUME_FACTOR = 1.5  # retail box + master carton air gap over the product bounding box (assumption)
MIN_PACKED_M3 = 0.0005  # a retail box is never smaller than ~0.5 L, even for a card (assumption)
FEU20_M3 = 33.0
FEU20_RATE_FACTOR = 0.55  # 20ft rate ≈ 0.55 × 40ft rate (assumption)
LCL_PREMIUM = 1.5  # LCL consolidation premium vs FCL per m³, typical 1.3-2.0× (assumption)
LCL_MIN_M3 = 1.0  # minimum LCL charge per shipment
DEFAULT_LANE = "Shanghai-Los Angeles"
EAST_COAST_LANE = "Shanghai-New York"


@lru_cache(maxsize=1)
def wci() -> dict:
    return json.loads(WCI_FILE.read_text())


def lane_rate(lane: str | None) -> tuple[float, str, str, str] | None:
    """(USD per 40ft, lane, as_of, source_url) or None when the lane is not in the snapshot."""
    d = wci()
    lane = lane or DEFAULT_LANE
    rate = d["lanes"].get(lane)
    return (float(rate), lane, d["as_of"], d["source_url"]) if rate is not None else None


def as_of_text(as_of: str | None = None) -> str:
    dt = date.fromisoformat(as_of or wci()["as_of"])
    return f"{dt.day} {dt.strftime('%b %Y')}"


def packed_volume_m3(l_mm: float, w_mm: float, h_mm: float) -> float:
    return max(l_mm * w_mm * h_mm / 1e9 * PACK_VOLUME_FACTOR, MIN_PACKED_M3)


def units_per_feu(volume_m3: float) -> int:
    return max(1, math.floor(FEU_USABLE_M3 / max(volume_m3, 1e-6)))


def fcl_per_unit(lane: str | None, volume_m3: float, qty: int) -> tuple[float, str, int] | None:
    """(cost per unit, container type, containers) of the cheapest whole-container option for a run of `qty` units."""
    lr = lane_rate(lane)
    if lr is None or volume_m3 <= 0 or qty <= 0:
        return None
    total = volume_m3 * qty
    n40, n20 = math.ceil(total / FEU_USABLE_M3), math.ceil(total / FEU20_M3)
    c40, c20 = n40 * lr[0], n20 * lr[0] * FEU20_RATE_FACTOR
    return (c20 / qty, "20ft", n20) if c20 < c40 else (c40 / qty, "40ft", n40)


def lcl_per_unit(lane: str | None, volume_m3: float, qty: int) -> tuple[float, float, float] | None:
    """(cost per unit, chargeable m³, USD per m³): lane rate ÷ 67 m³ × premium, minimum 1 m³ per shipment."""
    lr = lane_rate(lane)
    if lr is None or volume_m3 <= 0 or qty <= 0:
        return None
    per_m3 = lr[0] / FEU_USABLE_M3 * LCL_PREMIUM
    chargeable = max(volume_m3 * qty, LCL_MIN_M3)
    return per_m3 * chargeable / qty, chargeable, per_m3


def cheaper_sea_mode(lane: str | None, volume_m3: float, qty: int) -> str | None:
    lcl, fcl = lcl_per_unit(lane, volume_m3, qty), fcl_per_unit(lane, volume_m3, qty)
    if lcl is None or fcl is None:
        return None
    return "sea_lcl" if lcl[0] <= fcl[0] else "sea_fcl"


def citation(lane: str | None) -> str:
    lr = lane_rate(lane)
    return f"Drewry World Container Index, {as_of_text(lr[2])}: {lr[1].replace('-', '–')} ${lr[0]:,.0f}/40ft" if lr else ""
