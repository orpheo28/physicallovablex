"""Shared helpers of the engineering layer (private: not auto-imported by discovery)."""

from __future__ import annotations

import re

from contracts.artifacts import Label, LabeledValue

G = 9.81  # m/s²


def lv(value: float, unit: str, label: Label | str, note: str, nd: int = 2) -> LabeledValue:
    return LabeledValue(value=round(float(value), nd), unit=unit, label=Label(label), source_or_assumption=note)


def est(value: float, unit: str, note: str, nd: int = 2) -> LabeledValue:
    return lv(value, unit, Label.estimate, note, nd)


_RANK = {"measured": 0, "sourced": 0, "estimate": 1, "fictional": 2}


def weakest(*labels: object) -> str:
    """Label of a figure computed from several inputs: the least reliable input wins."""
    vals = [str(getattr(x, "value", x)) for x in labels if x is not None]
    return max(vals, key=lambda x: _RANK.get(x, 1)) if vals else "estimate"


def label_of(v: LabeledValue) -> str:
    return str(getattr(v.label, "value", v.label))


def first_number(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text or "", re.I)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except (ValueError, IndexError):
        return None
