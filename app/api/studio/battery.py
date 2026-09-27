"""Battery upgrades in the Studio (W21b): "longer flight time", "longer battery life", "more runtime" change the product.

    wants_battery(text) -> bool                          # a requirement that is really a battery change
    upgrade(project, arts, factor=None, capacity=None) -> (VersionChange | None, note | None)
    runtime(project, arts) -> (label, LabeledValue) | None   # flight time (drone) or battery life, from the engineering layer

The BOM battery line gets the new capacity (or a pack line is added from the category default), its price scales with the
capacity (Estimate) and the added mass is stated; the engineering checks (hover time, battery life, drone class by mass)
are recomputed on the new BOM, so the change shows a before → after figure instead of a noted requirement.
"""

from __future__ import annotations

import re

from contracts.artifacts import BOMCategory, BOMItem, Label, LabeledValue, VersionChange

LINE = re.compile(r"batter|li-?po|li-?ion|\bcell\b|\bpack\b|18650|21700|lifepo", re.I)
NOT_LINE = re.compile(r"charg|holder|bms|protect|gauge|connector|clip|contact", re.I)
WANTS = re.compile(r"(longer|more|extend\w*|increas\w*|bigger|double|better)\b.{0,25}(flight|battery|runtime|run[- ]time|autonomy|endurance)"
                   r"|(flight|battery|run)[- ]?(time|life)\b.{0,15}(longer|more|up)|\bbattery life\b|bigger battery|larger battery", re.I)
WH_PER_KG = 180.0  # Li-ion / Li-Po pack gravimetric energy density used for the mass delta (Estimate)
MAX_FACTOR = 3.0


def wants_battery(text: str) -> bool:
    return bool(WANTS.search(text or ""))


def _pack(project, arts) -> dict:
    from api.cad.family_mode import family_of
    from api.engineering.category import detect_category, load_pack
    from api.studio import product as P

    brief = arts.get(1)
    d = P.chosen(arts.get(2))
    text = " ".join(x for x in [project.prompt, project.name, getattr(brief, "product_name", ""), getattr(brief, "one_liner", "")] if x)
    return load_pack(detect_category(text.lower(), getattr(brief, "category", None), family_of(d) if d else None))


def _line(spec) -> BOMItem | None:
    return next((b for b in spec.bom if LINE.search(f"{b.part} {b.description or ''}") and not NOT_LINE.search(b.part)), None)


def _mah(text: str) -> float | None:
    m = re.search(r"(\d{2,6}(?:[.,]\d+)?)\s*mah", text or "", re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def _volts(text: str, params: dict) -> float:
    m = re.search(r"(\d)\s*s\b", text or "", re.I)
    if m:
        return 3.7 * int(m.group(1))
    v = re.search(r"(\d{1,2}(?:\.\d)?)\s*v\b", text or "", re.I)
    return float(v.group(1)) if v else float(params.get("battery_v_default", 3.7))


def upgrade(project, arts: dict, factor: float | None = None, capacity: float | None = None) -> tuple[VersionChange | None, str | None]:
    """Mutates arts[3] (spec BOM). Returns the component change, or (None, reason) when the product has no battery."""
    spec, brief = arts.get(3), arts.get(1)
    params = _pack(project, arts).get("params", {})
    line = _line(spec)
    if line is None and not (getattr(brief, "has_battery", False) or params.get("battery_mah_default")):
        return None, "No battery in this product: runtime is not modelled"
    text = f"{line.part} {line.description or ''}" if line else ""
    cur = _mah(text) or float(params.get("battery_mah_default") or 1000)
    new = capacity if capacity and capacity > 0 else cur * (factor or 1.5)
    new = round(max(cur * 1.05, min(new, cur * MAX_FACTOR)) / 10) * 10
    volts = _volts(text, params)
    dg = (new - cur) / 1000 * volts / WH_PER_KG * 1000
    if line is not None:
        if _mah(line.part):
            line.part = re.sub(r"\d{2,6}(?:[.,]\d+)?\s*mAh", f"{new:.0f} mAh", line.part, count=1, flags=re.I)
        else:
            line.part = f"{line.part.rstrip()}, {new:.0f} mAh"[:80]
        if line.unit_cost_est is not None:
            line.unit_cost_est = LabeledValue(value=round(line.unit_cost_est.value * new / cur, 4), unit="USD", label="estimate",
                                              source_or_assumption=f"Previous price × capacity ratio {new:.0f}/{cur:.0f} mAh (larger cell, Estimate)")
        line.lcsc_pn = None
        line.description = f"Upgraded in Studio: {cur:.0f} → {new:.0f} mAh at {volts:.1f} V (+{dg:.0f} g at {WH_PER_KG:.0f} Wh/kg)"
        before = f"{cur:.0f} mAh"
    else:
        from api.studio.product import next_bom_id

        spec.bom.append(BOMItem(id=next_bom_id(spec.bom, "electronic"), part=f"Li-ion battery pack {volts:.1f} V, {new:.0f} mAh",
                                category=BOMCategory.electronic, qty=1,
                                description=f"Added in Studio for runtime (+{new / 1000 * volts / WH_PER_KG * 1000:.0f} g at {WH_PER_KG:.0f} Wh/kg)"))
        before, dg = None, new / 1000 * volts / WH_PER_KG * 1000
    ch = VersionChange(area="component", label="Battery capacity", before=before,
                       after=f"{new:.0f} mAh at {volts:.1f} V ({new / 1000 * volts:.1f} Wh), +{dg:.0f} g", label_kind=Label.estimate)
    return ch, None


def runtime(project, arts: dict) -> tuple[str, LabeledValue] | None:
    """Flight time (drone) or battery life, computed by the engineering layer on these artifacts (no firmware written)."""
    from api.engineering.service import compute
    from api.stages.registry import StageContext

    try:
        eng = compute(StageContext(project=project, stage=0, artifacts=dict(arts)), llm_firmware=False, with_firmware=False)
    except Exception:  # noqa: BLE001
        return None
    for cid, label in (("hover_time", "Flight time"), ("battery_life", "Battery life")):
        c = next((x for x in eng.checks if x.id == cid), None)
        if c is not None:
            return label, c.value
    return None


def runtime_change(project, before: dict, after: dict) -> VersionChange | None:
    b, a = runtime(project, before), runtime(project, after)
    if a is None:
        return None
    fmt = lambda v: f"{v.value:.1f} {v.unit}"  # noqa: E731
    return VersionChange(area="performance", label=a[0], before=fmt(b[1]) if b else None, after=fmt(a[1]),
                         label_kind=a[1].label)


__all__ = ["wants_battery", "upgrade", "runtime", "runtime_change"]
