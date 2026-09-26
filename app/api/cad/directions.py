"""Stage 2 — Industrial design: 3 parametric directions built with build123d. Owner: W2.

One direction per generic family (soft rounded box, puck, slim slab). The LLM ("fast" route) proposes
names, dimensions, material and finish from the brief; every number is validated and clamped by
`api.cad.build.normalize`. If the LLM is unavailable or invalid, deterministic defaults by brief category
are used (generated_by="code"). Each direction is built (STEP/STL/GLB, cached by params hash) and its GLB is
served at /files/<project_id>/<direction_id>.glb.

Look (W12): each direction also carries a colour (in its finish, e.g. "Soft-touch paint · Sage #9DB09A").
dN.glb is the full product (shells + feet, button, light pipe, port, diffuser/bowl) with PBR materials
(api.cad.look); dN.step/stl stay the two moulded shells. While the CAD builds, one AI concept render per
direction is generated in parallel (api.cad.renders) → render_url, or None if no image model / timeout.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Literal

from pydantic import BaseModel, Field

from api.cad.build import FAMILIES, FAMILY_CODES, build_direction, normalize, project_dir
from api.cad.look import apply_materials, build_assembly, colour_of, describe_features, features_for, look_for
from api.cad.renders import RENDER_CAPTION, render_direction
from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import Assumption, DesignArtifact, DesignDirection, Dimensions, LabeledValue

log = logging.getLogger("cad.directions")

MATERIALS = {"pc_abs": "PC/ABS (UL94 V-0)", "aluminium": "Aluminium 6063-T5"}
DENSITY_G_CM3 = {"pc_abs": 1.15, "aluminium": 2.70}


# --------------------------------------------------------------------------- deterministic defaults

_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    # category keyword → per family (length, width, height, fillet, edge_fillet)
    "small": {  # wearables, trackers, cards, tags
        "rounded_box": dict(length=60, width=40, height=14, fillet=10, edge_fillet=2.5),
        "puck": dict(length=42, width=42, height=11, fillet=0, edge_fillet=2.5),
        "slab": dict(length=86, width=54, height=9, fillet=5, edge_fillet=1.5, wall=1.5),
    },
    "lighting": {
        "rounded_box": dict(length=140, width=90, height=40, fillet=22, edge_fillet=4),
        "puck": dict(length=110, width=110, height=35, fillet=0, edge_fillet=5),
        "slab": dict(length=160, width=70, height=22, fillet=8, edge_fillet=3),
    },
    "home": {  # kitchen, pet, appliances
        "rounded_box": dict(length=160, width=120, height=60, fillet=25, edge_fillet=5),
        "puck": dict(length=150, width=150, height=45, fillet=0, edge_fillet=6),
        "slab": dict(length=200, width=140, height=25, fillet=12, edge_fillet=3),
    },
    "default": {
        "rounded_box": dict(length=100, width=70, height=30, fillet=14, edge_fillet=3),
        "puck": dict(length=80, width=80, height=25, fillet=0, edge_fillet=4),
        "slab": dict(length=120, width=70, height=15, fillet=6, edge_fillet=2),
    },
}

_TEXT = {
    "rounded_box": ("Soft block", "Soft rounded box with generous corner radii and a split line at 60% height.",
                    "Rounded rectangular box", "MT-11010 light texture"),
    "puck": ("Puck", "Low cylindrical puck, two drafted shells, fits the palm.", "Cylinder / puck", "Soft-touch paint"),
    "slab": ("Slim slab", "Thin flat slab with tight radii — the most compact envelope.", "Slim rounded slab", "Polished SPI-B2"),
}
_COLOUR = {"rounded_box": ("Warm white", "#EDEBE6"), "puck": ("Graphite", "#3A3D42"), "slab": ("Sage", "#9DB09A")}
STAGE_BUDGET_S = 27.0  # renders are abandoned after this (cap, measured from the start of stage 2)
INLINE_RENDER_S = float(os.getenv("STAGE2_INLINE_S", "12"))
# Images are ~80% of the LLM spend: auto-render only the first N directions; the others on demand
# (POST /projects/{id}/stages/2/render?direction_id=dN).


def max_auto_renders() -> int:
    try:
        return max(0, int(os.getenv("LLM_IMAGE_MAX_RENDERS", "1")))
    except ValueError:
        return 1  # stage 2 answers after this; later renders are patched in


def preset_key(brief) -> str:
    text = " ".join(
        str(x) for x in [getattr(brief, "category", ""), getattr(brief, "product_name", ""), getattr(brief, "prompt", "")]
    ).lower()
    if any(k in text for k in ("track", "wallet", "card", "tag", "wear", "ring", "key", "earbud", "band")):
        return "small"
    if any(k in text for k in ("lamp", "light", "lighting")):
        return "lighting"
    if any(k in text for k in ("bowl", "kitchen", "pet", "dog", "cat", "home", "speaker", "appliance", "plant")):
        return "home"
    return "default"


# --------------------------------------------------------------------------- LLM schema


class DirectionProposal(BaseModel):
    family: Literal["rounded_box", "puck", "slab"]
    name: str = Field(max_length=40)
    description: str = Field(max_length=300)
    length_mm: float
    width_mm: float
    height_mm: float
    corner_radius_mm: float
    material: Literal["pc_abs", "aluminium"] = "pc_abs"
    finish: str = Field(max_length=60)
    colour_name: str = Field(default="", max_length=30)
    colour_hex: str = Field(default="", max_length=7)


class DirectionsProposal(BaseModel):
    directions: list[DirectionProposal] = Field(min_length=3, max_length=3)


PROMPT = """Product brief:
- name: {name}
- one-liner: {one_liner}
- category: {category}
- key features: {features}
- battery: {battery}; wireless: {wireless}

Propose exactly 3 enclosure design directions, one per family, in this order: rounded_box, puck, slab.
Each is a two-shell injection-moulded enclosure (wall 2.0 mm, draft 1.5°). Give realistic outer dimensions in mm
that fit the electronics implied by the brief, a corner radius, a material (pc_abs default; aluminium only if the
brief calls for a premium metal body) and a finish (e.g. 'MT-11010 light texture', 'Soft-touch paint', 'Polished').
Give each direction a distinct, tasteful colour (colour_name, e.g. 'Warm white', 'Sage', 'Graphite', and its sRGB
colour_hex '#RRGGBB'). Names are 1-2 evocative words (never a real brand). Descriptions are one sentence."""


def _propose_llm(brief) -> tuple[list[DirectionProposal], str]:
    from api.llm import complete_json, model_for

    prompt = PROMPT.format(
        name=brief.product_name, one_liner=brief.one_liner, category=brief.category,
        features="; ".join(brief.key_features), battery=brief.has_battery, wireless=", ".join(brief.wireless) or "none",
    )
    out = complete_json("fast", prompt, DirectionsProposal, max_tokens=1500)
    by_family = {d.family: d for d in out.directions}
    if set(by_family) != set(FAMILY_CODES):
        raise ValueError("LLM did not return one direction per family")
    return [by_family[f] for f in ("rounded_box", "puck", "slab")], f"llm:{model_for('fast')}"


def _defaults(brief) -> list[DirectionProposal]:
    preset = _PRESETS[preset_key(brief)]
    out = []
    for fam in ("rounded_box", "puck", "slab"):
        p = preset[fam]
        name, desc, _, finish = _TEXT[fam]
        cname, chex = _COLOUR[fam]
        out.append(DirectionProposal(family=fam, name=name, description=desc, length_mm=p["length"], width_mm=p["width"],
                                     height_mm=p["height"], corner_radius_mm=p["fillet"], material="pc_abs", finish=finish,
                                     colour_name=cname, colour_hex=chex))
    return out


def cad_params(prop: DirectionProposal, brief=None) -> dict[str, float]:
    extra = _PRESETS[preset_key(brief)][prop.family] if brief is not None else {}
    raw = {
        "family": FAMILY_CODES[prop.family], "length": prop.length_mm, "width": prop.width_mm, "height": prop.height_mm,
        "fillet": prop.corner_radius_mm, "edge_fillet": extra.get("edge_fillet", 3.0), "wall": extra.get("wall", 2.0),
        "draft_deg": 1.5, "split_ratio": 0.6, "boss_count": 4,
    }
    return normalize(raw)


def _lv(v: float, what: str) -> LabeledValue:
    return LabeledValue(value=round(v, 1), unit="mm", label="estimate", source_or_assumption=f"Design parameter ({what}), built in CAD")


def colour(prop: DirectionProposal) -> tuple[str, str]:
    """(name, #hex) of the direction; LLM values are checked, the family default fills gaps."""
    hex_ = colour_of(prop.colour_hex) or colour_of(prop.colour_name) or colour_of(prop.finish)
    name = prop.colour_name.strip() or _COLOUR[prop.family][0]
    return name, hex_ or _COLOUR[prop.family][1]


def direction_obj(project_id: str, did: str, prop: DirectionProposal, params: dict[str, float]) -> DesignDirection:
    """The DesignDirection without building anything (renders start from it while the CAD builds)."""
    cname, chex = colour(prop)
    finish = prop.finish if chex in prop.finish else f"{prop.finish} · {cname} {chex}"
    return DesignDirection(
        id=did, name=prop.name, description=prop.description, shape=_TEXT[prop.family][2],
        material=MATERIALS[prop.material], finish=finish,
        dimensions=Dimensions(length=_lv(params["length"], "length"), width=_lv(params["width"], "width"),
                              height=_lv(params["height"], "height")),
        cad_parameters={**params, "density_g_cm3": DENSITY_G_CM3[prop.material]},
        glb_url=f"/files/{project_id}/{did}.glb",
    )


def build_look(project_id: str, d: DesignDirection, params: dict[str, float], features: set[str]) -> None:
    """dN.glb = full product with materials; if the assembly fails, the shells GLB gets the materials."""
    look = look_for(d.material, d.finish)
    glb = project_dir(project_id) / f"{d.id}.glb"
    try:
        build_assembly(params, glb, look, features)
    except Exception as e:  # noqa: BLE001 — the plain shells are still a valid viewer model
        log.warning("assembly %s failed, shells only: %s", d.id, e)
        try:
            apply_materials(glb, look)
        except Exception as e2:  # noqa: BLE001
            log.warning("materials %s failed: %s", d.id, e2)


def make_direction(project_id: str, did: str, prop: DirectionProposal, params: dict[str, float],
                   features: set[str] | None = None) -> DesignDirection:
    build_direction(params, project_dir(project_id), name=did)
    d = direction_obj(project_id, did, prop, params)
    build_look(project_id, d, params, features if features is not None else {"button", "led", "feet", "port"})
    return d


def _url(f) -> str | None:
    return f.result() if f.done() and not f.cancelled() and f.exception() is None else None


def _render_assumption() -> Assumption:
    return Assumption(id="a2_render", label="estimate", stage=2,
                      text=f"{RENDER_CAPTION}. Images generated by an AI image model from the brief and each "
                           "direction's shape, dimensions, material, finish and colour; the 3D model is the CAD.")


def _patch_late_renders(pid: str, pending: dict, deadline: float, started: datetime) -> None:
    """Renders that finish after stage 2 answered (≤ STAGE_BUDGET_S) are written into the saved artifact."""
    from api.stages import runner

    wait(pending.values(), timeout=max(0.0, deadline - time.monotonic()))
    urls = {did: u for did, f in pending.items() if (u := _url(f))}
    if not urls:
        return
    for _ in range(40):  # the runner saves the artifact right after the handler returns
        art = runner.get_artifact(pid, 2)
        if art is not None and not art.fallback and art.generated_at >= started and {d.id for d in art.directions} >= set(urls):
            for d in art.directions:
                if d.id in urls and not d.render_url:
                    d.render_url = urls[d.id]
            if not any(a.id == "a2_render" for a in art.assumptions):
                art.assumptions.append(_render_assumption())
            runner.save_artifact(pid, 2, art, art.status)
            log.info("stage 2 %s: %d late render(s) patched in", pid, len(urls))
            return
        time.sleep(0.25)


def render_on_demand(project_id: str, direction_id: str) -> DesignArtifact:
    """Render one direction now (same 25 s call timeout, 27 s budget) and store its render_url in the saved stage 2.
    Never raises for a failed render: the artifact comes back with render_url unchanged (None)."""
    from api.stages import runner

    art, brief = runner.get_artifact(project_id, 2), runner.get_artifact(project_id, 1)
    if art is None:
        raise LookupError("stage 2 not run yet")
    d = next((x for x in art.directions if x.id == direction_id), None)
    if d is None:
        raise KeyError(direction_id)
    if d.render_url:
        return art
    feats = features_for(brief) if brief is not None else set()
    url = render_direction(project_id, brief, d, project_dir(project_id), colour_name=None,
                           extra=describe_features(feats), deadline=time.monotonic() + STAGE_BUDGET_S)
    if url:
        art = runner.get_artifact(project_id, 2) or art  # re-read: the user may have chosen a direction meanwhile
        for x in art.directions:
            if x.id == direction_id:
                x.render_url = url
        if not any(a.id == "a2_render" for a in art.assumptions):
            art.assumptions.append(_render_assumption())
        runner.save_artifact(project_id, 2, art, art.status)
    return art


@stage_handler(2)
def run(ctx: StageContext) -> DesignArtifact:
    t0, started = time.monotonic(), datetime.now(timezone.utc)
    brief = ctx.artifact(1)
    if brief is None:
        raise LookupError("stage 2 needs the brief (stage 1)")
    assumptions = [Assumption(id="a2_1", label="estimate", stage=2,
                              text="Two-shell injection-moulded enclosure, nominal wall 2.0 mm, 1.5° draft, split line at 60% height, 4 × M2.5 screw bosses")]
    try:
        proposals, generated_by = _propose_llm(brief)
    except Exception as e:  # noqa: BLE001 — deterministic defaults are a first-class path, not a fallback
        log.info("stage 2 LLM unavailable, using category defaults: %s", e)
        proposals, generated_by = _defaults(brief), "code"
        assumptions.append(Assumption(id="a2_2", label="estimate", stage=2,
                                      text=f"Dimensions from '{preset_key(brief)}' category presets (LLM unavailable: {type(e).__name__})"))
    pid = ctx.project.id
    params = [cad_params(p, brief) for p in proposals]
    directions = [direction_obj(pid, f"d{i + 1}", p, params[i]) for i, p in enumerate(proposals)]
    features = features_for(brief)

    # ≤ LLM_IMAGE_MAX_RENDERS images per run (first directions), in parallel with the (CPU-bound) CAD builds
    deadline = t0 + STAGE_BUDGET_S
    pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="render")
    futures = {d.id: pool.submit(render_direction, pid, brief, d, project_dir(pid), colour_name=colour(p)[0],
                                 extra=describe_features(features), deadline=deadline)
               for d, p in list(zip(directions, proposals))[:max_auto_renders()]}
    try:
        for d, p in zip(directions, params):
            build_direction(p, project_dir(pid), name=d.id)
            build_look(pid, d, p, features)
    finally:
        # answer quickly: wait for the images only up to the inline budget; the rest is patched in later (≤ deadline)
        wait(futures.values(), timeout=max(0.0, min(deadline, t0 + INLINE_RENDER_S) - time.monotonic()))
        pool.shutdown(wait=False, cancel_futures=False)
    pending = {}
    for d in directions:
        f = futures.get(d.id)
        d.render_url = _url(f) if f is not None else None
        if f is not None and not f.done():
            pending[d.id] = f
    if any(d.render_url for d in directions):
        assumptions.append(_render_assumption())
    if pending:
        threading.Thread(target=_patch_late_renders, args=(pid, pending, deadline, started), daemon=True,
                         name=f"renders-{pid}").start()
    prev = ctx.artifact(2)
    chosen = prev.chosen_direction_id if prev is not None and prev.chosen_direction_id in {d.id for d in directions} else None
    return DesignArtifact(project_id=ctx.project.id, generated_by=generated_by, assumptions=assumptions,
                          directions=directions, chosen_direction_id=chosen)


__all__ = ["run", "cad_params", "make_direction", "direction_obj", "build_look", "preset_key", "DENSITY_G_CM3", "MATERIALS", "FAMILIES"]
