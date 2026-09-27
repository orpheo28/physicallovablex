"""Deterministic parametric product families (W19) — seeds and fallbacks for the text-to-CAD engine.

    names() -> ["board", "furniture", "stick_vacuum", "home_robot", "irrigation", "solar_array",
                "drone", "hair_dryer", "camera", "smartphone"]                  # the last four: W21
    params_for(name, variant=None, **overrides) -> dict[str, float]      # clamped, fits DesignDirection.cad_parameters
    build_family(name, params) -> (Compound, [labelled parts])           # in-process, < 1 s
    export_family(name, out_dir, stem, params=None, colour=None) -> {"files": {step, stl, glb}, "measured", "params"}
    seed_code_for(name, params) -> str                                   # stand-alone build123d program (codegen seed)

Wearables (band / ring) are W17's families in api/cad/build.py (family codes 3 / 4), not duplicated here.
"""

from __future__ import annotations

import importlib
from dataclasses import asdict
from pathlib import Path
from typing import Any

from api.cad.families._common import (EXTRA_ROLES, ROLES, apply_look, export_parts, family_look,  # noqa: F401
                                      measure_parts, seed_code)

_MODULES = ("board", "furniture", "stick_vacuum", "home_robot", "irrigation", "solar_array", "drone", "hair_dryer",
            "camera", "smartphone")
# body colour of the viewer GLB when the caller gives none (accent = a shade of it, see look.look_for)
DEFAULT_COLOUR = {"board": "#4F6F95", "furniture": "#F2F2EF", "stick_vacuum": "#9A9DA1", "home_robot": "#F2F2EF",
                  "irrigation": "#EDEBE6", "solar_array": "#9A9DA1", "drone": "#3A3D42", "hair_dryer": "#E8E4DC",
                  "camera": "#2B2D30", "smartphone": "#3A3D42"}


def names() -> list[str]:
    return list(_MODULES)


def module(name: str):
    if name not in _MODULES:
        raise KeyError(f"unknown family {name!r} (known: {', '.join(_MODULES)})")
    return importlib.import_module(f"api.cad.families.{name}")


def params_for(name: str, variant: str | None = None, **overrides: float) -> dict[str, float]:
    m = module(name)
    base = m.default_params(variant) if variant else m.default_params()
    raw = {**base, **{k: float(v) for k, v in overrides.items() if k in base and v is not None}}
    return asdict(m.Params(**raw).clamped())


def build_family(name: str, params: dict[str, Any] | None = None):
    return module(name).build(params_for(name, **(params or {})))


def export_family(name: str, out_dir: Path | str, stem: str, params: dict[str, Any] | None = None,
                  colour: str | None = None) -> dict[str, Any]:
    from api.cad.parts import trace_labels

    p = params_for(name, **(params or {}))
    with trace_labels(module(name).__file__) as sites:
        _, parts = module(name).build(p)
    from api.cad.family_mode import part_names

    files = export_parts(parts, Path(out_dir) / stem, family_look(colour or DEFAULT_COLOUR.get(name)),
                         names=part_names(name, sites, [q.label for q in parts]))
    return {"files": files, "measured": measure_parts(parts), "params": p}


def seed_code_for(name: str, params: dict[str, Any] | None = None) -> str:
    return seed_code(module(name), params_for(name, **(params or {})))
