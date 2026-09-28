"""CAD_DETAIL_LEVEL switch (basic | pro, default pro since C5; basic = the pre-C1 CAD). Read at call time so tests / the Monitor can flip it."""

from __future__ import annotations

import os

LEVELS = ("basic", "pro")
DEFAULT = "pro"  # C5: on by default (CAD_DETAIL_LEVEL=basic restores the pre-C1 CAD)


def detail_level(override: str | None = None) -> str:
    v = (override or os.getenv("CAD_DETAIL_LEVEL") or DEFAULT).strip().lower()
    return v if v in LEVELS else "basic"  # a value we do not know: the conservative CAD


def is_pro(override: str | None = None) -> bool:
    return detail_level(override) == "pro"
