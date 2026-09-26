"""Shared planning constants and formulas for stages 6, 9 and 10 (private module)."""

from __future__ import annotations

import math
from datetime import date, timedelta

from contracts.artifacts import ProcessType

P = ProcessType

# Region *clusters* (public geography, never a factory name).
REGION_BY_PROCESS: dict[str, str] = {
    P.injection_molding.value: "Dongguan, Guangdong",
    P.cnc.value: "Dongguan, Guangdong",
    P.sheet_metal.value: "Dongguan, Guangdong",
    P.die_casting.value: "Ningbo, Zhejiang",
    P.extrusion.value: "Foshan, Guangdong",
    P.pcba.value: "Shenzhen, Guangdong",
    P.assembly.value: "Shenzhen, Guangdong",
    P.other.value: "Shenzhen, Guangdong",
}

# Lead time in days = tooling (if any) + first shots / first article. Planning assumptions.
LEAD_TIME_DAYS: dict[str, int] = {
    P.injection_molding.value: 35,
    P.die_casting.value: 40,
    P.extrusion.value: 20,
    P.sheet_metal.value: 15,
    P.cnc.value: 10,
    P.pcba.value: 12,
    P.assembly.value: 7,
    P.other.value: 14,
}

TOOLED = {P.injection_molding.value, P.die_casting.value, P.extrusion.value, P.sheet_metal.value}

T1_DAYS = 14  # tooling correction round
GOLDEN_SAMPLE_DAYS = 7
UNITS_PER_DAY = 90  # mass-production output assumption for a small SME line
MIN_MASS_DAYS = 14
PSI_UNITS_PER_MAN_DAY = 100  # units checked per inspector-day incl. functional tests
TRANSIT_SEA_DAYS = 32
DELIVERY_DAYS = 3
DEFAULT_LOT = 2000


def mass_days(qty: int) -> int:
    return max(MIN_MASS_DAYS, math.ceil(qty / UNITS_PER_DAY))


def tooling_lead_days(steps: list[tuple[str, int]]) -> int:
    """T0 duration from (process, lead_time_days) pairs: slowest tooled part, else slowest first article."""
    tooled = [d for p, d in steps if p in TOOLED]
    pool = tooled or [d for _, d in steps]
    return max(pool) if pool else LEAD_TIME_DAYS[P.injection_molding.value]


def t1_days(steps: list[tuple[str, int]]) -> int:
    return T1_DAYS if any(p in TOOLED for p, _ in steps) else 7


def total_lead_days(steps: list[tuple[str, int]], qty: int) -> int:
    """T0 + T1 + golden sample + mass production (from PO, excluding shipping)."""
    return tooling_lead_days(steps) + t1_days(steps) + GOLDEN_SAMPLE_DAYS + mass_days(qty)


# ISO 2859-1 (ANSI/ASQ Z1.4) Table 1 (General II) and Table 2-A (single sampling, normal).
_LOT_TABLE: list[tuple[int, str, int]] = [
    (8, "A", 2), (15, "B", 3), (25, "C", 5), (50, "D", 8), (90, "E", 13), (150, "F", 20), (280, "G", 32),
    (500, "H", 50), (1200, "J", 80), (3200, "K", 125), (10000, "L", 200), (35000, "M", 315),
    (150000, "N", 500), (500000, "P", 800),
]  # fmt: skip
_LAST = ("Q", 1250)
# Acceptance numbers (Ac) by sample size for AQL 2.5 and 4.0 (Re = Ac + 1).
_AC = {
    2.5: {20: 1, 32: 2, 50: 3, 80: 5, 125: 7, 200: 10, 315: 14, 500: 21},
    4.0: {20: 2, 32: 3, 50: 5, 80: 7, 125: 10, 200: 14, 315: 21},
}


def sample_size(lot: int) -> tuple[str, int]:
    """(code letter, sample size) for a lot size, inspection level General II."""
    lot = max(2, int(lot))
    for upper, letter, n in _LOT_TABLE:
        if lot <= upper:
            return letter, min(n, lot)
    return _LAST


def lot_range_text(lot: int) -> str:
    lo = 2
    for upper, _, _ in _LOT_TABLE:
        if lot <= upper:
            return f"{lo:,}–{upper:,}"
        lo = upper + 1
    return f"{lo:,}+"


def accept_reject(aql: float, n: int) -> tuple[int, int] | None:
    if aql == 0:
        return 0, 1
    ac = _AC.get(aql, {}).get(n)
    return (ac, ac + 1) if ac is not None else None


def inspection_man_days(n: int) -> int:
    return max(1, math.ceil(n / PSI_UNITS_PER_MAN_DAY))


def next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)
