"""Auto-discovery of Wave 1 plug-ins. Owner: W0.

At startup every Python module under the owned folders (api/cad, api/dfm, api/costs, api/agents,
api/agents/negotiation, api/export, and any new sub-package of api/) is imported. Importing a module runs its
@stage_handler / @provider decorators. If a module defines `register(router: APIRouter)`, it is called once.
A module that fails to import is logged and skipped — the affected stage keeps serving fixtures.

Files whose name starts with `_` or `test_` (and `conftest`) are skipped (keep private helpers/tests there).
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("discovery")

API_DIR = Path(__file__).resolve().parent
SKIP_TOP = {"main", "discovery", "db", "llm", "stages", "fixtures", "data"}


def _iter_modules() -> list[str]:
    names: list[str] = []

    def walk(path: Path, prefix: str) -> None:
        for m in pkgutil.iter_modules([str(path)]):
            if m.name.startswith(("_", "test_")) or m.name == "conftest":
                continue
            full = prefix + m.name
            if prefix == "api." and m.name in SKIP_TOP:
                continue
            names.append(full)
            if m.ispkg:
                walk(path / m.name, full + ".")

    walk(API_DIR, "api.")
    return names


def discover(router: APIRouter) -> list[str]:
    loaded: list[str] = []
    for name in _iter_modules():
        try:
            mod = importlib.import_module(name)
        except Exception as e:  # noqa: BLE001
            log.error("plug-in %s failed to import (stage keeps fixture fallback): %s", name, e)
            continue
        reg = getattr(mod, "register", None)
        if callable(reg) and getattr(reg, "__module__", None) == mod.__name__:
            try:
                reg(router)
            except Exception as e:  # noqa: BLE001
                log.error("plug-in %s register() failed: %s", name, e)
                continue
        loaded.append(name)
    log.info("discovered plug-ins: %s", loaded)
    return loaded
