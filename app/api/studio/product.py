"""Product state readers shared by Studio start / refine (W17): shape family choice, material vocabulary, known
components, wearable certification rows, the Version preview and the before/after change list.
"""

from __future__ import annotations

import re

from api.agents.certification import _cert
from api.cad.build import FAMILIES, normalize
from api.cad.look import COLOURS, colour_of
from contracts.artifacts import (
    BOMItem,
    Certification,
    Label,
    VersionChange,
    VersionFactory,
    VersionPreview,
    VersionUnitCost,
)

# --------------------------------------------------------------------------- shape family

_RING = re.compile(r"\b(smart ?ring|sleep ring|ring)\b", re.I)
_BAND = re.compile(r"\b(whoop|fitness (band|tracker)|wrist ?band|wristband|strap|bracelet|wearable band|activity tracker|"
                   r"heart[- ]rate (band|strap|monitor)|hrv (band|strap)|recovery (band|tracker)|band)\b", re.I)


def studio_family(brief, prompt: str = "") -> str | None:
    """'ring' | 'wearable_band' for wearables, else None (the stage-2 LLM families stay)."""
    text = " ".join(str(x) for x in [prompt, getattr(brief, "product_name", ""), getattr(brief, "one_liner", ""),
                                     getattr(brief, "category", ""), " ".join(getattr(brief, "key_features", []) or [])])
    if _RING.search(text) and not re.search(r"\bring light\b|\bkey ?ring\b|\bring buoy\b", text, re.I):
        return "ring"
    if _BAND.search(text) or ("wearable" in text.lower() and "wrist" in text.lower()):
        return "wearable_band"
    return None


FAMILY_SHAPE = {
    "rounded_box": "Rounded rectangular box", "puck": "Cylinder / puck", "slab": "Slim rounded slab",
    "wearable_band": "Sensor pod on a strap", "ring": "Ring with inner sensor bump",
}
FAMILY_TEXT = {
    "wearable_band": "Screenless sensor pod on a soft strap: two drafted shells with an optical sensor window underneath.",
    "ring": "Smart ring: two drafted annular halves with a sensor bump on the inside of the band.",
}
AXIS_NAMES = {
    "wearable_band": ("Pod length", "Pod width", "Pod thickness"),
    "ring": ("Outer diameter", "Outer diameter", "Band width"),
}


def family_of(params: dict) -> str:
    return FAMILIES.get(int(params.get("family", 0)), "rounded_box")


# --------------------------------------------------------------------------- material vocabulary

MATERIALS = {  # key → (DesignDirection.material text, density g/cm³, default finish)
    "pc_abs": ("PC/ABS (UL94 V-0)", 1.15, "Soft-touch paint"),
    "aluminium": ("Aluminium 6063-T5", 2.70, "Bead-blasted anodised"),
    "stainless_steel": ("Stainless steel 316L", 8.0, "Brushed"),
    "tpu": ("TPU (soft-touch, Shore 85A)", 1.20, "Matte texture"),
}


def material_key(text: str) -> str:
    low = (text or "").lower()
    if "alumin" in low:
        return "aluminium"
    if "stainless" in low or "steel" in low:
        return "stainless_steel"
    if "tpu" in low:
        return "tpu"
    return "pc_abs"


# --------------------------------------------------------------------------- colour

_FIN = re.compile(r"^(?P<finish>.*?)\s*·\s*(?P<name>[^#]*?)\s*(?P<hex>#[0-9A-Fa-f]{6})?\s*$")


def split_finish(finish: str) -> tuple[str, str | None, str | None]:
    """'Soft-touch paint · Sage #9DB09A' → ('Soft-touch paint', 'Sage', '#9DB09A')."""
    m = _FIN.match(finish or "")
    if not m:
        return finish or "", None, colour_of(finish or "")
    return m.group("finish").strip(), (m.group("name") or "").strip() or None, (m.group("hex") or "").upper() or colour_of(finish)


def join_finish(finish: str, name: str | None, hex_: str | None) -> str:
    if not hex_:
        return finish
    return f"{finish} · {name or 'Custom'} {hex_}"


def valid_hex(hex_: str | None, name: str | None) -> str | None:
    if hex_ and re.fullmatch(r"#?[0-9A-Fa-f]{6}", hex_.strip()):
        return "#" + hex_.strip().lstrip("#").upper()
    return colour_of(name or "") if name else None


# --------------------------------------------------------------------------- known components (LCSC-matchable)

# keyword → (part, manufacturer_pn in the LCSC snapshot or None, category, why)
KNOWN_PARTS: list[tuple[re.Pattern, str, str | None, str]] = [
    (re.compile(r"heart|hrv|\bppg\b|pulse|spo2|oxygen|blood ox", re.I),
     "Optical heart-rate / SpO2 sensor (PPG, MAX30102)", "MAX30102EFD+T", "Optical PPG front end for heart rate, HRV and SpO2"),
    (re.compile(r"accelero|motion|step|activity|sleep stage|imu", re.I),
     "3-axis accelerometer (I²C)", None, "Motion / activity and sleep staging"),
    (re.compile(r"skin[- ]temp|body[- ]temp|temperature", re.I), "Skin temperature sensor, digital I²C ±0.1 °C (HDC3020)", "HDC3020DEFR",
     "Skin temperature trend (digital I²C, ±0.1 °C)"),
    (re.compile(r"haptic|vibrat", re.I), "Coin vibration motor 3 V", None, "Haptic alerts"),
]


# W21c: what a BOM line already provides — never add a second part for a capability the product has
CAPABILITY: dict[str, re.Pattern] = {
    "ppg": re.compile(r"heart|hrv|\bppg\b|pulse|spo2|oxygen|oximet|max3010|max86|afe44", re.I),
    "imu": re.compile(r"accelero|\bimu\b|gyro|motion sensor|6-axis|3-axis|qmi8658|bmi\d|lsm6|lis2", re.I),
    "temperature": re.compile(r"skin[- ]temp|body[- ]temp|temperature sensor|thermometer|hdc30|tmp1\d\d|max3020", re.I),
    "haptic": re.compile(r"haptic|vibrat", re.I),
}
SPO2 = re.compile(r"spo2|oxygen|oximet|max3010|red.{0,8}ir|red\s*\+\s*ir", re.I)


def capability(text: str) -> str | None:
    for cap, rx in CAPABILITY.items():
        if rx.search(text or ""):
            return cap
    return None


def provider(bom: list[BOMItem], cap: str) -> BOMItem | None:
    """The BOM line that already provides capability `cap` (electronic lines only)."""
    rx = CAPABILITY[cap]
    return next((b for b in bom if str(getattr(b.category, "value", b.category)) == "electronic"
                 and rx.search(f"{b.part} {b.manufacturer_pn or ''} {b.description or ''}")), None)


def known_parts(text: str) -> list[tuple[str, str | None, str]]:
    """Every catalogue part a capability text implies ('SpO2 and skin temperature' → PPG + temperature sensor)."""
    return [(part, pn, why) for rx, part, pn, why in KNOWN_PARTS if rx.search(text or "")]


def known_part(text: str) -> tuple[str, str | None, str] | None:
    for rx, part, pn, why in KNOWN_PARTS:
        if rx.search(text or ""):
            return part, pn, why
    return None


def next_bom_id(bom: list[BOMItem], category: str) -> str:
    prefix = {"electronic": "e", "mechanical": "m", "packaging": "k"}[category]
    nums = [int(m.group(1)) for b in bom if (m := re.fullmatch(prefix + r"(\d+)", b.id))]
    return f"{prefix}{max(nums, default=0) + 1}"


# --------------------------------------------------------------------------- wearable certification rows

_HEALTH = re.compile(r"heart|hrv|\bppg\b|pulse|spo2|oxygen|ecg|blood|health|recovery|sleep", re.I)
_OPTICAL = re.compile(r"ppg|optical|max3010|photodiode|heart", re.I)
_SPO2_TEMP = re.compile(r"spo2|oxygen|oximet|body[- ]temp|skin[- ]temp", re.I)


def studio_certs(brief, spec, family: str | None) -> list[Certification]:
    """Rows the rule-based map does not cover for body-worn products (skin contact, optical sensing, wellness claims)."""
    text = " ".join([getattr(brief, "one_liner", ""), getattr(brief, "category", ""), *(getattr(brief, "key_features", []) or []),
                     *(b.part for b in (getattr(spec, "bom", None) or []))])
    worn = family in ("wearable_band", "ring") or getattr(brief, "category", "") == "wearable"
    markets = " ".join(getattr(brief, "target_markets", []) or []).upper()
    rows: list[Certification] = []
    if worn:
        rows.append(_cert("Global", "ISO 10993-5 / -10 (skin-contact biocompatibility: cytotoxicity, sensitisation)",
                          "Worn against the skin for hours: retailers and EU market surveillance expect biocompatibility data for the skin-contact materials",
                          2500, 5, required=False, note=" — lower if the material supplier already holds reports"))
        if "EU" in markets:
            rows.append(_cert("EU", "REACH Annex XVII entry 27 (nickel release, EN 1811)",
                              "Items in prolonged skin contact must meet the nickel-release limit (metal parts, charging contacts)", 400, 2))
    if worn and _OPTICAL.search(text):
        if "EU" in markets or "UK" in markets:
            rows.append(_cert("EU", "IEC 62471 (photobiological safety of the optical sensor LEDs)",
                              "Optical heart-rate sensing shines LEDs (green / red / IR) into the skin: the risk group must be assessed", 1200, 3))
    if worn and _SPO2_TEMP.search(text) and "US" in markets:
        rows.append(_cert("US", "FDA general-wellness vs medical-device boundary (SpO2 / body-temperature claims)",
                          "SpO2 and body-temperature readings are medical-device functions unless marketed strictly as general wellness: "
                          "the claims, app wording and accuracy statements must be reviewed before sale (else 510(k) / De Novo)",
                          2500, 3, note=" — regulatory-consultant claims review, demo assumption"))
    if worn and _HEALTH.search(text) and "US" in markets:
        rows.append(_cert("US", "FDA general-wellness policy review (no medical claims)",
                          "Heart-rate / HRV / sleep metrics stay a non-regulated wellness product only while no diagnostic claim is made; a claims review avoids a 510(k)",
                          1500, 2, required=False, note=" — regulatory-consultant review, demo assumption"))
    return rows


def _cert_key(c: Certification) -> str:
    m = re.search(r"\d{3,6}", c.standard)
    return f"{c.market}:{m.group(0) if m else c.standard.lower()[:24]}"


def merge_certs(*groups: list[Certification]) -> list[Certification]:
    seen, out = set(), []
    for g in groups:
        for c in g:
            k = _cert_key(c)
            if k not in seen:
                seen.add(k)
                out.append(c)
    return out


def refresh_certs(brief, spec, previous: list[Certification], family: str | None) -> list[Certification]:
    """Rule-based map (no LLM) + wearable rows + the previous run's LLM-proposed rows (kept until the next AI pass)."""
    from api.agents.certification import rule_based

    llm_rows = [c for c in previous if "LLM-proposed" in (c.cost_est.source_or_assumption or "")]
    certs = merge_certs(rule_based(brief, spec), studio_certs(brief, spec, family), llm_rows)
    if not certs:
        certs = previous
    return certs


# --------------------------------------------------------------------------- preview + changes


def chosen(design):
    if design is None:
        return None
    return next((d for d in design.directions if d.id == design.chosen_direction_id), design.directions[0])


def _cad_fields(spec, d) -> dict:
    """W21: AI model first when present, its program, label and source (from the stage-3 CAD entries)."""
    from api.studio.cad import is_ai, source_of

    files = spec.cad_files if spec is not None else []
    ai = [f for f in files if is_ai(f)]
    glb = next((f.url for f in ai if f.format == "glb"), None)
    step = next((f.url for f in ai if f.format == "step"), None) or next(
        (f.url for f in files if f.format == "step" and (f.description or "").startswith("Full product")), None) or next(
        (f.url for f in files if f.format == "step"), None)
    py = next((f for f in files if f.format == "py"), None)
    return {"glb_url": glb or (d.glb_url if d else None), "step_url": step, "code_url": py.url if py else None,
            "cad_label": (py.description.split(" — build123d")[0] if py and py.description else None),
            "cad_source": source_of(py) if py else None}


def preview(arts: dict) -> VersionPreview:
    from api.cad.family_mode import family_of as product_family

    design, spec, dfm, costs, match = (arts.get(k) for k in (2, 3, 4, 5, 7))
    d = chosen(design)
    fin, cname, chex = split_finish(d.finish) if d else ("", None, None)
    cad = _cad_fields(spec, d)
    site = costs is not None and getattr(costs, "unit_basis", "per_unit") == "per_installation"
    return VersionPreview(
        **cad,
        unit_basis="per_installation" if site else "per_unit",
        installed_price=costs.target_retail_price if site else None,
        installer_cost=costs.tiers[0].unit_cost if site and costs.tiers else None,
        render_url=d.render_url if d else None,
        dimensions=spec.overall_dimensions if spec else None,
        color_hex=chex, color_name=cname,
        material=d.material if d else None, finish=fin or None,
        shape_family=(product_family(d) or family_of(normalize(d.cad_parameters))) if d and d.cad_parameters else None,
        unit_costs=[VersionUnitCost(quantity=t.quantity, value=round(t.unit_cost.value, 2), label=t.unit_cost.label,
                                    source_or_assumption=t.unit_cost.source_or_assumption) for t in (costs.tiers if costs else [])],
        top_factories=[VersionFactory(name=f.factory_name, score=round(f.score.value, 1)) for f in (match.shortlist[:3] if match else [])],
        certifications=[f"{c.market} {c.standard}" for c in (dfm.certifications if dfm else []) if c.required],
        bom_count=len(spec.bom) if spec else 0,
    )


def _mm(v) -> str:
    return f"{v:.1f} mm"


def _money(v: float, cur: str = "USD") -> str:
    return f"${v:,.2f}" if cur == "USD" else f"{v:,.2f} {cur}"


def _ref_unit(costs) -> tuple[float, int] | None:
    if costs is None or not costs.tiers:
        return None
    t = next((t for t in costs.tiers if t.quantity == costs.reference_quantity), costs.tiers[len(costs.tiers) // 2])
    return t.unit_cost.value, t.quantity


def changes(before: dict, after: dict) -> list[VersionChange]:
    out: list[VersionChange] = []

    def add(area, label, b, a, kind: Label | str = Label.estimate):
        out.append(VersionChange(area=area, label=label, before=b, after=a, label_kind=kind))

    b1, a1 = before.get(1), after.get(1)
    bd, ad = chosen(before.get(2)), chosen(after.get(2))
    if bd and ad:
        bfam, afam = family_of(normalize(bd.cad_parameters)), family_of(normalize(ad.cad_parameters))
        _, bn, bh = split_finish(bd.finish)
        _, an, ah = split_finish(ad.finish)
        if (bh or "") != (ah or ""):
            add("color", "Colour", f"{bn or ''} {bh or ''}".strip() or None, f"{an or ''} {ah or ''}".strip() or None)
        if bd.material != ad.material or split_finish(bd.finish)[0] != split_finish(ad.finish)[0]:
            add("material", "Material & finish", f"{bd.material}, {split_finish(bd.finish)[0]}", f"{ad.material}, {split_finish(ad.finish)[0]}")
        if bfam != afam:
            add("shape", "Shape", FAMILY_SHAPE.get(bfam, bfam), FAMILY_SHAPE.get(afam, afam))
    bs, as_ = before.get(3), after.get(3)
    if bs and as_:
        fam = family_of(normalize(ad.cad_parameters)) if ad else ""
        names = AXIS_NAMES.get(fam, ("Length", "Width", "Height"))
        for i, axis in enumerate(("length", "width", "height")):
            if fam == "ring" and axis == "width":
                continue
            bv, av = getattr(bs.overall_dimensions, axis).value, getattr(as_.overall_dimensions, axis).value
            if abs(bv - av) >= 0.05:
                add("dimensions", names[i], _mm(bv), _mm(av), getattr(as_.overall_dimensions, axis).label)
        if abs(bs.weight.value - as_.weight.value) >= 0.1:
            add("dimensions", "Enclosure weight", f"{bs.weight.value:.1f} g", f"{as_.weight.value:.1f} g", as_.weight.label)
        bids = {b.id: b for b in bs.bom}
        aids = {b.id: b for b in as_.bom}
        c5 = after.get(5)
        priced = {ln.bom_item_id: ln.unit_price for ln in (c5.bom_lines if c5 is not None else [])}
        per = "installation" if c5 is not None and getattr(c5, "unit_basis", "per_unit") == "per_installation" else "unit"
        for i, it in aids.items():
            if i not in bids:
                price = priced.get(i) or it.unit_cost_est  # W21e: the price stage 5 uses, not a stale BOM placeholder
                src = f" — LCSC {it.lcsc_pn}" if it.lcsc_pn else ""
                after_txt = f"{it.part} × {it.qty:g}{src}" + (f", {_money(price.value)}/{per}" if price else "")
                add("component", "Component added", None, after_txt, price.label if price else Label.estimate)
                out[-1].risk = component_risk_summary(it)
        for i, it in bids.items():
            if i not in aids:
                add("component", "Component removed", f"{it.part} × {it.qty:g}", None)
    if b1 and a1:
        for f in a1.key_features:
            if f not in b1.key_features:
                add("feature", "Feature", None, f)
        for f in b1.key_features:
            if f not in a1.key_features:
                add("feature", "Feature removed", f, None)
        bp, ap = b1.target_retail_price, a1.target_retail_price
        if (bp.value, bp.unit) != (ap.value, ap.unit):
            add("price", "Target retail price", _money(bp.value, bp.unit), _money(ap.value, ap.unit), ap.label)
        if b1.target_markets != a1.target_markets:
            add("markets", "Markets", " + ".join(b1.target_markets), " + ".join(a1.target_markets))
        for c in a1.constraints:
            if c not in b1.constraints:
                add("requirement", "Requirement (noted, not modelled)", None, c)
    bdf, adf = before.get(4), after.get(4)
    if bdf and adf:
        breq = {f"{c.market} {c.standard}" for c in bdf.certifications if c.required}
        areq = {f"{c.market} {c.standard}" for c in adf.certifications if c.required}
        for c in sorted(areq - breq):
            add("certification", "Certification required", None, c)
        for c in sorted(breq - areq):
            add("certification", "Certification no longer required", c, None)
    bc, ac = before.get(5), after.get(5)
    if bc and ac:
        bu, au = _ref_unit(bc), _ref_unit(ac)
        if bu and au and abs(bu[0] - au[0]) >= 0.005:
            per_site = getattr(ac, "unit_basis", "per_unit") == "per_installation"
            add("cost", "Installer cost per installation" if per_site else f"Unit cost @ {au[1]:,}", _money(bu[0]), _money(au[0]))
            if per_site and abs(bc.target_retail_price.value - ac.target_retail_price.value) >= 1:
                add("cost", "Installed price per roof", _money(bc.target_retail_price.value), _money(ac.target_retail_price.value))
        if abs(bc.tooling_total.value - ac.tooling_total.value) >= 1:
            add("cost", "Tooling", _money(bc.tooling_total.value), _money(ac.tooling_total.value))
        if abs(bc.certification_total.value - ac.certification_total.value) >= 1:
            add("cost", "Certification budget", _money(bc.certification_total.value), _money(ac.certification_total.value))
    return out


def component_risk_summary(item: BOMItem):
    """W21b: structured supply risk of an added part (level, reasons, cheaper in-stock alternative) for the UI."""
    from api.costs.lcsc import component_risk
    from contracts.artifacts import ComponentRiskSummary

    try:
        rows = component_risk([item])
    except Exception:  # noqa: BLE001
        return None
    if not rows:
        return None
    r = rows[0]
    return ComponentRiskSummary(level=r.level, reasons=list(r.reasons), alternative=r.alternative)


def summarize(chs: list[VersionChange], llm_summary: str = "") -> str:
    if llm_summary.strip():
        return llm_summary.strip()[:200]
    if not chs:
        return "No change to the product"
    return "; ".join(f"{c.label}: {c.after or 'removed'}" for c in chs[:4])[:200]


__all__ = ["studio_family", "FAMILY_SHAPE", "FAMILY_TEXT", "MATERIALS", "material_key", "split_finish", "join_finish",
           "valid_hex", "known_part", "next_bom_id", "studio_certs", "refresh_certs", "merge_certs", "chosen", "preview",
           "changes", "summarize", "family_of", "COLOURS"]
