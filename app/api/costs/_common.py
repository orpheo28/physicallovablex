"""Shared helpers for the costs package (labelled values, rounding, label combination)."""

from __future__ import annotations

from contracts.artifacts import Label, LabeledValue

SNAPSHOT_DATE = "2026-09-26"
LCSC_SOURCE = f"LCSC price, {SNAPSHOT_DATE}"
VTRUST_SOURCE = "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26"  # $268 per man-day pre-shipment inspection
EXTENDED_NOTE = "LCSC unit price (Sourced) × estimated quantity"


def lcsc_url(pn: str | None) -> str:
    return f"https://www.lcsc.com/product-detail/{pn}.html" if pn else "https://www.lcsc.com/"


def lcsc_source(pn: str | None, what: str = "price") -> str:
    """Sourced LCSC price/stock: product page URL + snapshot date (JLCPCB/LCSC parts snapshot)."""
    return f"LCSC {what}, snapshot {SNAPSHOT_DATE}, {lcsc_url(pn)}"

_RANK = {"sourced": 0, "measured": 0, "estimate": 1, "fictional": 2}


def lv(value: float, unit: str, label: str, note: str, nd: int = 2) -> LabeledValue:
    return LabeledValue(value=round(float(value), nd), unit=unit, label=Label(label), source_or_assumption=note)


def usd(value: float, label: str, note: str, nd: int = 2) -> LabeledValue:
    return lv(value, "USD", label, note, nd)


def weakest(*labels: str) -> str:
    """Label of a figure derived from several inputs: the least reliable one wins (sourced < estimate < fictional)."""
    ls = [str(getattr(x, "value", x)) for x in labels]
    return max(ls, key=lambda x: _RANK.get(x, 1))


def label_of(v: LabeledValue) -> str:
    return str(getattr(v.label, "value", v.label))
