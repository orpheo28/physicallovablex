"""LCSC/JLCPCB snapshot matcher and component risk. Owner: W3.

Public API (signatures are a cross-session contract, see README.md):
    match_bom(items: list[BOMItem], order_qty: int = 2000) -> list[BOMItem]
    component_risk(items: list[BOMItem]) -> list[ComponentRiskItem]
    price_at(lcsc_pn, qty) -> float | None ; stock_of(lcsc_pn) -> int | None
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from contracts.artifacts import BOMCategory, BOMItem, ComponentRiskItem, RiskLevel

from ._common import LCSC_SOURCE, SNAPSHOT_DATE, lcsc_source, lv

DATA = Path(__file__).resolve().parent / "data" / "jlcpcb_parts.csv"
LOW_STOCK = 1000
CRITICAL_STOCK = 100


@dataclass(frozen=True)
class Part:
    lcsc: int
    category: str
    subcategory: str
    mfr: str
    package: str
    manufacturer: str
    library_type: str
    preferred: bool
    description: str
    stock: int
    breaks: tuple[tuple[int, float], ...]

    @property
    def pn(self) -> str:
        return f"C{self.lcsc}"

    @property
    def text(self) -> str:
        return f"{self.mfr} {self.subcategory} {self.description} {self.package}".lower()

    def price(self, qty: int) -> float:
        p = self.breaks[0][1]
        for lo, price in self.breaks:
            if qty >= lo:
                p = price
        return p


def _parse_breaks(s: str) -> tuple[tuple[int, float], ...]:
    out = []
    for chunk in s.split(","):
        rng, _, price = chunk.partition(":")
        lo = rng.split("-")[0]
        if lo.isdigit() and price:
            try:
                out.append((int(lo), float(price)))
            except ValueError:
                pass
    return tuple(sorted(out))


@lru_cache(maxsize=1)
def parts() -> tuple[Part, ...]:
    rows: list[Part] = []
    with DATA.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            br = _parse_breaks(r["price"])
            if not br:
                continue
            rows.append(
                Part(
                    lcsc=int(r["lcsc"]),
                    category=r["category"],
                    subcategory=r["subcategory"],
                    mfr=r["mfr"],
                    package=r["package"],
                    manufacturer=r["manufacturer"],
                    library_type=r["library_type"],
                    preferred=r["preferred"] == "1" or r["basic"] == "1",
                    description=r["description"],
                    stock=int(float(r["stock"] or 0)),
                    breaks=br,
                )
            )
    return tuple(rows)


@lru_cache(maxsize=1)
def _by_pn() -> dict[str, Part]:
    return {p.pn: p for p in parts()}


def get_part(lcsc_pn: str | None) -> Part | None:
    return _by_pn().get((lcsc_pn or "").upper())


def price_at(lcsc_pn: str, qty: int) -> float | None:
    p = get_part(lcsc_pn)
    return p.price(max(1, int(qty))) if p else None


def stock_of(lcsc_pn: str) -> int | None:
    p = get_part(lcsc_pn)
    return p.stock if p else None


# --------------------------------------------------------------------------- matching

# (regex on part text, category, subcategory substring, required tokens in part text, any-of tokens)
RULES: list[tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = [
    # passives first: "USB-C CC pull-down resistors" is a resistor line, not a connector
    (r"resistor", "Resistors", "", (), ()),
    (r"capacitor", "Capacitors", "", (), ()),
    (r"\bdiodes?\b", "Diodes", "", (), ()),
    (r"usb[- ]?c|type-c|usb type c", "Connectors", "USB", ("type-c",), ()),
    (r"charger|charging|lipo|li-?ion (charge|manag)|tp4056|4056|bms", "Power Management (PMIC)", "Battery", (), ("charg", "4056")),
    (r"\bmcu\b|microcontroller|stm32|esp32|nrf5", "Embedded Processors & Controllers", "", (), ()),
    (r"\bldo\b|linear regulator|3\.3 ?v regulator", "Power Management (PMIC)", "LDO", (), ()),
    (r"dc-?dc|buck|boost converter", "Power Management (PMIC)", "DC-DC", (), ()),
    (r"mosfet|n-?ch|p-?ch", "Transistors/Thyristors", "MOSFET", (), ()),
    (r"schottky", "Diodes", "Schottky", (), ()),
    (r"\besd\b|tvs", "Circuit Protection", "ESD", (), ()),
    (r"\bled\b", "Optoelectronics", "LED", (), ()),
    (r"accelerometer|imu|sensor", "Sensors", "", (), ()),
    (r"crystal|oscillator", "Crystals, Oscillators, Resonators", "", (), ()),
    (r"\bbuzzer\b", "Audio Products / Vibration Motors", "", (), ()),
    (r"tactile|push ?button|switch", "Switches", "", (), ()),
]

# Lines that are not catalogue parts: never match, estimate instead.
NOT_CATALOGUE = re.compile(r"\bcell\b|18650|21700|battery|lipo pack|\bpcb\b|pcba|mcpcb|assembled|cable|antenna|harness|enclosure|circuit board", re.I)
# MCU/SoC families: a line naming one only matches a part of that family (never a random MCU from another vendor)
FAMILIES = re.compile(r"esp32(?:-[a-z]\d)?|stm32[a-z]?\d*|nrf5\d*|rp2040|ch32v?\d*|atmega\d*|attiny\d*|py32|gd32|samd\d*", re.I)
# Lines that name a mains/non-battery "cell" (load cell, solar cell) are not batteries
NOT_BATTERY_CELL = re.compile(r"load[- ]?cells?|solar[- ]?cells?|peltier|cellular|cell phone", re.I)
STOP = {"smd", "ic", "the", "and", "for", "with", "type", "chip", "pin", "pcs", "of", "a", "in", "to", "(esop-8)", "led"}
DEFAULT_ESTIMATES = {  # USD per unit, used only when neither the LCSC snapshot nor the input BOM give a price (most specific first)
    "load cell": 2.40, "wi-fi": 2.20, "esp32": 2.20, "ble module": 2.50, "bluetooth module": 2.50, "lte": 12.0,
    "display": 6.00, "motor": 1.20, "sensor": 0.90, "mcpcb": 0.35, "pcb": 0.60, "circuit board": 0.60,
    "cell": 2.40, "cable": 0.45, "antenna": 0.15, "module": 1.50,
}


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\.]+", s.lower()) if len(t) >= 2 and t not in STOP]


def _pkg_tokens(s: str) -> set[str]:
    return {m.lower() for m in re.findall(r"(?:sop|esop|soic|sot|qfn|dfn|tssop|msop|lqfp|qfp|ssop)[- ]?\d+[a-z0-9\-]*", s, re.I)}


def best_match(text: str, mfr_pn: str | None = None, order_qty: int = 2000, part: str | None = None) -> Part | None:
    """Best snapshot part for a free-text BOM line, or None. `part` (the line's name) decides the class before the
    description does: "USB keyboard controller MCU — with USB-C" is an MCU, not a connector."""
    if NOT_CATALOGUE.search(text) and not mfr_pn:
        return None
    if mfr_pn:
        hits = [p for p in parts() if p.mfr.lower() == mfr_pn.lower() and p.stock >= 5]
        if hits:
            return max(hits, key=lambda p: p.stock)
    low = text.lower()
    # 1. an explicit part number inside the text ("N-MOSFET AO3400A", "TP4056")
    named = re.findall(r"[a-z]{1,4}\d{3,}[a-z0-9\-]*", low)
    for tok in named:
        hits = [p for p in parts() if tok in p.mfr.lower()]
        if hits:
            return _rank(hits, low, order_qty)
    if named:  # a specific part number that is not in the snapshot: do not substitute a different part silently
        return None
    # 2. class rule
    fams = [f.lower() for f in FAMILIES.findall(low)]
    heads = [part.lower()] if part else []
    ordered = [r for h in heads for r in RULES if re.search(r[0], h)] + [r for r in RULES if re.search(r[0], low)]
    for pattern, cat, sub, need, anyof in dict.fromkeys(ordered):
        pool = [p for p in parts() if p.category == cat and (not sub or sub.lower() in p.subcategory.lower())]
        if fams:  # named family (ESP32, STM32, nRF52…): same family or no match
            pool = [p for p in pool if any(f in p.mfr.lower() for f in fams)]
        pool = [p for p in pool if p.stock >= LOW_STOCK] or pool
        if need:
            pool = [p for p in pool if all(n in p.text for n in need)]
        if anyof:
            pool = [p for p in pool if any(n in p.text for n in anyof)]
        if pool:
            return _rank(pool, low, order_qty)
    return None


def _rank(pool: list[Part], text: str, order_qty: int) -> Part:
    pkgs = _pkg_tokens(text)
    toks = set(_tokens(text))

    def score(p: Part) -> tuple:
        pk = 1 if pkgs and any(x in p.package.lower().replace(" ", "") for x in pkgs) else 0
        overlap = sum(1 for t in toks if t in p.text)
        # generic class match: a basic/preferred, well-stocked and cheap part (never the premium outlier of the class)
        return (pk, p.preferred or p.library_type == "base", overlap, min(p.stock, 100000) >= 5000, -p.price(order_qty), p.stock)

    return max(pool, key=score)


def _default_estimate(item: BOMItem) -> tuple[float, str]:
    def keyed(low: str) -> tuple[float, str] | None:
        k = next((k for k in DEFAULT_ESTIMATES if k in low), None)
        return (DEFAULT_ESTIMATES[k], f"Placeholder estimate for a '{k}' line (not a catalogue part): USD {DEFAULT_ESTIMATES[k]:.2f} per unit") if k else None

    if hit := keyed(item.part.lower()):  # the line's name first
        return hit
    if item.qty > 20:
        return 0.08, f"Placeholder estimate: USD 0.08 per piece for a small part used {item.qty:g}× per unit"
    if hit := keyed((item.description or "").lower()):
        return hit
    return 0.30, "Placeholder estimate: USD 0.30 per unit for an electronic line without catalogue match"


def match_bom(items: list[BOMItem], order_qty: int = 2000) -> list[BOMItem]:
    """Electronic lines → LCSC part (lcsc_pn, Sourced unit_cost_est at the qty break of order_qty × qty per unit).

    Unmatched electronic lines keep their own price if the input had one (Estimate) or get a placeholder Estimate
    with the assumption spelled out. Non-electronic lines are returned unchanged. Input is not mutated.
    """
    out: list[BOMItem] = []
    for it in items:
        it = it.model_copy(deep=True)
        if it.category != BOMCategory.electronic and str(it.category) != "electronic":
            out.append(it)
            continue
        text = f"{it.part} {it.description or ''}"
        part = best_match(text, it.manufacturer_pn, order_qty, part=it.part)
        if part is not None:
            n = max(1, int(round(order_qty * it.qty)))
            it.lcsc_pn = part.pn
            it.manufacturer_pn = it.manufacturer_pn or part.mfr
            it.unit_cost_est = lv(part.price(n), "USD", "sourced", lcsc_source(part.pn), nd=4)
            it.description = it.description or f"{part.manufacturer} {part.mfr} {part.package} — {part.subcategory}"
            pk = _pkg_tokens(text)
            if pk and not any(x in part.package.lower().replace(" ", "") for x in pk):
                it.alternative = it.alternative or "Closest class match in the snapshot, package differs from the request: verify pinout and footprint"
        else:
            it.lcsc_pn = None
            if it.unit_cost_est is not None:
                it.unit_cost_est = lv(
                    it.unit_cost_est.value, "USD", "estimate",
                    f"No match in LCSC snapshot {SNAPSHOT_DATE}; price from BOM input: {it.unit_cost_est.source_or_assumption}",
                    nd=4,
                )
            else:
                v, why = _default_estimate(it)
                it.unit_cost_est = lv(v, "USD", "estimate", f"No match in LCSC snapshot {SNAPSHOT_DATE}. {why}", nd=4)
        out.append(it)
    return out


# --------------------------------------------------------------------------- risk


def alternatives_for(p: Part, k: int = 3) -> list[Part]:
    """Same subcategory + package, different part, in stock; best stock first."""
    pool = [
        q for q in parts()
        if q.lcsc != p.lcsc and q.subcategory == p.subcategory and q.package == p.package and q.stock >= LOW_STOCK
    ]
    # closer description first (shared tokens), then stock
    pt = set(_tokens(p.description))
    pool.sort(key=lambda q: (-len(pt & set(_tokens(q.description))), -q.stock))
    return pool[:k]


def component_risk(items: list[BOMItem]) -> list[ComponentRiskItem]:
    """Risk per electronic line (and any Li-ion cell): low stock, extended part, single source, unmatched."""
    res: list[ComponentRiskItem] = []
    for it in items:
        cat = str(getattr(it.category, "value", it.category))
        low = f"{it.part} {it.description or ''}".lower()
        is_cell = (bool(re.search(r"\b(cell|pack)\b|18650|21700", it.part.lower())) and not re.search(r"charg|\bic\b", it.part.lower())
                   and not NOT_BATTERY_CELL.search(it.part))
        if cat != "electronic" and not is_cell:
            continue
        reasons: list[str] = []
        alts: list[str] = []
        level = RiskLevel.low
        stock = None
        p = get_part(it.lcsc_pn)
        if p is not None:
            stock = lv(p.stock, "units", "sourced", lcsc_source(p.pn, "stock"), nd=0)
            if p.stock < CRITICAL_STOCK:
                reasons.append(f"very low stock ({p.stock} pcs)")
                level = RiskLevel.high
            elif p.stock < LOW_STOCK:
                reasons.append(f"low stock ({p.stock} pcs)")
                level = RiskLevel.medium
            if p.library_type != "base" and not p.preferred:
                reasons.append("JLCPCB extended part (per-part-type feeder fee at assembly)")
            alt = alternatives_for(p)
            alts = [f"{a.pn} {a.mfr} ({a.package}, {a.stock} in stock, ${a.price(2000):.4f}@2k)" for a in alt]
            if not alt:
                reasons.append("single source: no same-package alternative in the snapshot")
                level = RiskLevel.high if level == RiskLevel.high else RiskLevel.medium
        elif not is_cell:
            reasons.append(f"not matched to the LCSC snapshot {SNAPSHOT_DATE}: availability and price unverified")
            level = RiskLevel.medium
        if is_cell:
            reasons.append("Li-ion cell: UN38.3 transport test, air-freight restrictions, protection circuit required")
            level = RiskLevel.medium if level == RiskLevel.low else level
        res.append(
            ComponentRiskItem(
                bom_item_id=it.id, part=it.part, level=level, reasons=reasons or ["in stock, basic/preferred part, alternatives available"],
                alternatives=alts, stock=stock, lead_time_weeks=None,
            )
        )
    return res
