"""Fastener catalogue for the assembly (C2): screws, heat-set inserts, spring bars → FastenerUse rows and BOM lines.

Dimensions and unit prices come from C1's `api.cad.stdparts` (ISO 14583 pan head screws, McMaster-Carr 94459A heat-set
inserts, catalogue prices at ~2,000 pcs, Estimate) when it is importable; otherwise from the built-in copy below (same
standards, fewer sizes). `SOURCE` says which one answered.

    size_for(span_mm) -> "M2" | "M2.5" | "M3" | "M4"   # screw size from the joint's scale
    insert_length(size) -> mm ; nominal(size) -> mm ; screw_length(min_len) -> standard length ≥ min_len
    uses_for_screwed(size, screw_len, qty, insert) -> [FastenerUse]
    bom_lines(uses) -> [BOMItem]    # aggregated by designation; LCSC-matched → Sourced, else Estimate
"""

from __future__ import annotations

import logging
from typing import Any

from contracts.artifacts import BOMCategory, BOMItem, FastenerUse, LabeledValue

log = logging.getLogger("cad.assembly.fasteners")

try:  # C1 (CAD_DETAIL_LEVEL=pro) standard parts — optional
    from api.cad.stdparts import hardware as _hw  # type: ignore[import-not-found]
    from api.cad.stdparts import tables as _T  # type: ignore[import-not-found]

    SOURCE = "api.cad.stdparts"
except Exception:  # noqa: BLE001 — not merged yet / broken: built-in table
    _hw = _T = None
    SOURCE = "built-in table"

# built-in fallback (same standards as C1's tables): ISO 14583 pan head Torx; McMaster-Carr 94459A heat-set inserts
_NOMINAL = {"M1.6": 1.6, "M2": 2.0, "M2.5": 2.5, "M3": 3.0, "M4": 4.0, "M5": 5.0}
_INSERT_LEN = {"M2": 4.0, "M2.5": 4.0, "M3": 5.7, "M4": 8.2, "M5": 9.5}
_PRICE = {"screw": {"M2": 0.020, "M2.5": 0.022, "M3": 0.025, "M4": 0.035, "M5": 0.045},
          "insert": {"M2": 0.06, "M2.5": 0.07, "M3": 0.08, "M4": 0.11, "M5": 0.14}}
SPRING_BAR_PRICE = 0.04  # stainless spring bar Ø1.5 mm (watch-strap type), catalogue order of magnitude
# ISO 14583 preferred lengths (mm)
SCREW_LENGTHS = (3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30)
PRICE_NOTE = "Catalogue order of magnitude at ~2,000 pcs (Estimate, not a quote)"


def nominal(size: str) -> float:
    if _T is not None and size in getattr(_T, "NOMINAL", {}):
        return float(_T.NOMINAL[size])
    return _NOMINAL[size]


def insert_length(size: str) -> float:
    if _T is not None and size in getattr(_T, "INSERT_HEATSET", {}):
        return float(_T.INSERT_HEATSET[size][1])
    return _INSERT_LEN[size]


def size_for(span_mm: float) -> str:
    """Screw size from the size of the joined part (rule of thumb: M2 small wearables/drones, M2.5 handhelds, M3 housings
    up to ~40 cm, M4 above)."""
    return "M2" if span_mm < 60 else "M2.5" if span_mm < 150 else "M3" if span_mm < 400 else "M4"


def screw_length(min_len: float) -> float:
    return float(next((x for x in SCREW_LENGTHS if x >= min_len - 1e-6), SCREW_LENGTHS[-1]))


def _screw_std(size: str) -> str:
    return "ISO 14583 (hexalobular pan head), A2 stainless"


def _insert_std(size: str) -> str:
    pn = None
    if _T is not None and size in getattr(_T, "INSERT_HEATSET", {}):
        pn = _T.INSERT_HEATSET[size][3]
    return f"Heat-set brass insert (McMaster-Carr {pn})" if pn else "Heat-set brass insert (catalogue class)"


def uses_for_screwed(size: str, length: float, qty: int, insert: bool) -> list[FastenerUse]:
    out = [FastenerUse(kind="screw", standard=_screw_std(size), designation=f"{size}×{length:g}", size=size, length_mm=length,
                       qty=qty, source=SOURCE)]
    if insert:
        li = insert_length(size)
        out.append(FastenerUse(kind="insert", standard=_insert_std(size), designation=f"{size}×{li:g}", size=size, length_mm=li,
                               qty=qty, source=SOURCE))
    return out


def spring_bars(qty: int, length: float) -> list[FastenerUse]:
    return [FastenerUse(kind="spring_bar", standard="Spring bar Ø1.5 mm, 316L stainless (watch-strap type)",
                        designation=f"Ø1.5×{length:.0f}", size="Ø1.5", length_mm=round(length, 1), qty=qty, source="built-in table")]


def _unit_price(u: FastenerUse) -> tuple[float, str]:
    if u.kind == "spring_bar":
        return SPRING_BAR_PRICE, PRICE_NOTE
    if _hw is not None:
        try:
            sp = _hw.screw(u.size, u.length_mm, "pan") if u.kind == "screw" else _hw.heat_set_insert(u.size)
            return float(sp.bom["unit_price_usd"]), sp.bom.get("price_source") or PRICE_NOTE
        except Exception as e:  # noqa: BLE001
            log.info("stdparts price unavailable for %s: %s", u.designation, e)
    table = _PRICE["screw" if u.kind == "screw" else "insert"]
    return table.get(u.size, 0.03), PRICE_NOTE


def _part_text(u: FastenerUse) -> str:
    if u.kind == "screw":
        return f"Screw {u.size} × {u.length_mm:g} pan head T-drive ({u.standard})"
    if u.kind == "insert":
        return f"Heat-set threaded insert {u.designation} ({u.standard})"
    return f"Spring bar {u.designation} mm ({u.standard})"


def bom_lines(uses: list[FastenerUse], match_lcsc: bool = True) -> list[BOMItem]:
    """Aggregate by (kind, designation) → BOMItem ids fx1… ; LCSC snapshot match first (Sourced), else Estimate."""
    agg: dict[tuple[str, str], dict[str, Any]] = {}
    for u in uses:
        k = (u.kind, u.designation)
        row = agg.setdefault(k, {"use": u, "qty": 0})
        row["qty"] += u.qty
    items = []
    for i, ((kind, _), row) in enumerate(sorted(agg.items()), 1):
        u = row["use"]
        price, note = _unit_price(u)
        items.append(BOMItem(id=f"fx{i}", part=_part_text(u), category=BOMCategory.mechanical, qty=float(row["qty"]),
                             description=f"Fastener aggregated from the assembly joints ({u.source})",
                             unit_cost_est=LabeledValue(value=round(price, 4), unit="USD", label="estimate", source_or_assumption=note)))
    if match_lcsc and items:
        try:
            from api.costs import lcsc

            matched = lcsc.match_bom(items, order_qty=2000)
            # keep only confident mechanical matches (the snapshot is electronics-heavy): the part text must name the size
            items = [m if m.lcsc_pn and _plausible(m, it) else it for m, it in zip(matched, items)]
        except Exception as e:  # noqa: BLE001
            log.info("LCSC match skipped for fasteners: %s", e)
    return items


def _plausible(m: BOMItem, it: BOMItem) -> bool:
    from api.costs.lcsc import get_part

    p = get_part(m.lcsc_pn)
    if p is None:
        return False
    size = it.part.split()[1] if len(it.part.split()) > 1 else ""
    return any(w in p.text for w in ("screw", "insert", "spring")) and size.lower() in p.text


__all__ = ["SOURCE", "size_for", "insert_length", "nominal", "screw_length", "uses_for_screwed", "spring_bars", "bom_lines"]
