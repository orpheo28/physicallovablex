"""BOM for stage 5: from stage 3 spec, else pasted BOM, else LLM proposal ('fast'), else category template. Owner: W3.

    load_bom(ctx) -> (items, generated_by, notes)   # items are already run through lcsc.match_bom
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from api import llm
from api.stages.registry import StageContext
from contracts.artifacts import BOMCategory, BOMItem

from ._common import lv
from .lcsc import match_bom

log = logging.getLogger("costs.bom")
MIN_LINES = 4  # a spec BOM with fewer lines is "thin"


class _Line(BaseModel):
    part: str
    category: BOMCategory
    qty: float = Field(gt=0)
    description: str | None = None
    est_unit_cost_usd: float | None = Field(default=None, ge=0, description="Rough unit cost at ~2,000 pcs")


class BOMProposal(BaseModel):
    items: list[_Line] = Field(min_length=4, max_length=40)


def _mk(prefix: str, rows: list[tuple[str, float, float | None]], cat: BOMCategory, start: int = 1) -> list[BOMItem]:
    out = []
    for i, (part, qty, cost) in enumerate(rows, start):
        out.append(
            BOMItem(
                id=f"{prefix}{i}", part=part, category=cat, qty=qty,
                unit_cost_est=lv(cost, "USD", "estimate", "Template BOM price assumption, no spec available", nd=4) if cost is not None else None,
            )
        )
    return out


def template_bom(text: str) -> tuple[str, list[BOMItem]]:
    low = text.lower()
    if any(w in low for w in ("tracker", "wallet", "tag", "finder")):
        e = [("BLE SoC module with antenna", 1, None), ("USB-C receptacle 16P SMD", 1, None), ("LiPo charger IC", 1, None),
             ("LDO 3.3V regulator", 1, None), ("Piezo buzzer", 1, None), ("Tactile push button", 1, None), ("Accelerometer", 1, None),
             ("Li-ion cell 40 mAh thin", 1, 0.9), ("Control PCB 4-layer, assembled", 1, 0.55)]
        m = [("PC enclosure shell top", 1, 0.35), ("PC enclosure shell bottom", 1, 0.3), ("Silicone gasket", 1, 0.05)]
        k = [("Retail blister pack", 1, 0.3), ("Quick-start card", 1, 0.03)]
        name = "tracker_card"
    elif any(w in low for w in ("lamp", "lampe", "light")):
        e = [("White LED 2835 4000K", 24, None), ("LiPo charger IC", 1, None), ("USB-C receptacle 16P SMD", 1, None), ("N-MOSFET", 1, None),
             ("Touch-dimming MCU 8-bit SOP-8", 1, None), ("Li-ion cell 18650 3000 mAh", 1, 2.4), ("Aluminium MCPCB for LED bar", 1, 0.35),
             ("Control PCB 2-layer, assembled", 1, 0.6)]
        m = [("Head housing, PC/ABS", 1, 0.95), ("Diffuser, opal PC", 1, 0.3), ("Stem, aluminium extrusion", 1, 1.6),
             ("Base shell, PC/ABS", 1, 1.1), ("Steel weight plate", 1, 0.7), ("Neodymium magnet", 4, 0.08), ("Fastener set", 1, 0.1)]
        k = [("Retail box with pulp insert", 1, 0.9), ("USB-C cable 1 m", 1, 0.45)]
        name = "desk_lamp"
    else:
        e = [("MCU 32-bit", 1, None), ("USB-C receptacle 16P SMD", 1, None), ("LDO 3.3V regulator", 1, None), ("Status LED", 2, None),
             ("Tactile push button", 1, None), ("Control PCB 2-layer, assembled", 1, 0.6)]
        m = [("Injection-moulded housing top", 1, 0.8), ("Injection-moulded housing bottom", 1, 0.8), ("Fastener set", 1, 0.1)]
        k = [("Retail box", 1, 0.7), ("Quick-start guide", 1, 0.05)]
        name = "generic"
    return name, _mk("e", e, BOMCategory.electronic) + _mk("m", m, BOMCategory.mechanical) + _mk("k", k, BOMCategory.packaging)


def llm_bom(text: str) -> list[BOMItem]:
    prop = llm.complete_json(
        "fast",
        "Propose a realistic bill of materials (one line per distinct part, electronic parts described generically "
        "such as 'USB-C receptacle 16P' or 'LiPo charger IC', with quantity per finished unit and a rough unit cost "
        f"in USD at ~2,000 pcs) for this product: {text}",
        BOMProposal,
    )
    pre = {"electronic": "e", "mechanical": "m", "packaging": "k"}
    items = []
    for i, ln in enumerate(prop.items, 1):
        cat = str(getattr(ln.category, "value", ln.category))
        items.append(
            BOMItem(
                id=f"{pre[cat]}{i}", part=ln.part, category=ln.category, qty=ln.qty, description=ln.description,
                unit_cost_est=lv(ln.est_unit_cost_usd, "USD", "estimate", "LLM-proposed price, not verified", nd=4) if ln.est_unit_cost_usd is not None else None,
            )
        )
    return items


def load_bom(ctx: StageContext, order_qty: int = 2000) -> tuple[list[BOMItem], str, list[str]]:
    """Returns (matched BOM, generated_by, notes)."""
    spec, brief = ctx.artifact(3), ctx.artifact(1)
    notes: list[str] = []
    text = " ".join(filter(None, [ctx.project.prompt, getattr(brief, "product_name", None), getattr(brief, "one_liner", None), getattr(brief, "category", None)]))
    gen = "code"
    if spec is not None and len(spec.bom) >= MIN_LINES:
        items, notes = list(spec.bom), ["BOM from stage 3 spec"]
    elif brief is not None and len(getattr(brief, "pasted_bom", []) or []) >= MIN_LINES:
        items, notes = list(brief.pasted_bom), ["BOM from the pasted BOM (prototype mode)"]
    else:
        items = []
        if llm.is_configured("fast"):
            try:
                items = llm_bom(text)
                gen, notes = f"llm:{llm.model_for('fast')}", ["BOM lines proposed by the LLM (spec missing or thin); prices matched and computed in code"]
            except Exception as e:  # noqa: BLE001
                log.info("LLM BOM proposal failed → template: %s", e)
        if not items:
            name, items = template_bom(text)
            notes = [f"Template BOM for category '{name}' (no spec BOM available): review before relying on it"]
    return match_bom(items, order_qty), gen, notes
