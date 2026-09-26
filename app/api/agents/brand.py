"""Stage 13 — Brand kit. Owner: W4.

LLM (route "fast") writes names, packaging text, landing copy and listing drafts. Python owns every number:
box dimensions (product size + clearance), packaging unit cost (from the BOM), listing prices (from the brief).
Handler raises on any LLM failure → the runner serves the fixture.
"""

from __future__ import annotations

from contracts.artifacts import (
    Dimensions,
    LabeledValue,
    LandingCopy,
    Label,
    ListingDraft,
    NameOption,
    PackagingSpec,
    BrandArtifact,
)
from pydantic import BaseModel, ConfigDict, Field

from api.agents._common import AssumptionLog, estimate, llm_tag, lv, render_prompt
from api.llm import complete_json
from api.stages.registry import StageContext, stage_handler

CLEARANCE_MM = 10.0
DEFAULT_PACKAGING_USD = 1.2
EUR_USD = 1.08  # same demo assumption as the cached example (stage 1)


class _Name(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    rationale: str


class _Listing(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    description: str
    bullets: list[str] = Field(min_length=3, max_length=8)
    keywords: list[str] = Field(default_factory=list, max_length=12)


class BrandDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name_options: list[_Name] = Field(min_length=3, max_length=5)
    box_type: str
    box_materials: list[str] = Field(min_length=1)
    printing: str
    contents: list[str] = Field(min_length=1)
    headline: str
    subheadline: str
    landing_bullets: list[str] = Field(min_length=3, max_length=6)
    cta: str
    shopify: _Listing
    amazon: _Listing


def _dim(value: float, why: str) -> LabeledValue:
    return lv(round(value, 1), "mm", Label.estimate, why)


def packaging_dimensions(spec) -> Dimensions:
    """Retail box: the product's three sizes sorted, plus clearance each (a rule, not a design)."""
    o = spec.overall_dimensions
    sizes = sorted([o.length.value, o.width.value, o.height.value], reverse=True)
    why = f"Product overall size + {CLEARANCE_MM:g} mm clearance (rule; insert design at packaging RFQ)"
    return Dimensions(length=_dim(sizes[0] + CLEARANCE_MM, why), width=_dim(sizes[1] + CLEARANCE_MM, why), height=_dim(sizes[2] + CLEARANCE_MM, why))


def packaging_unit_cost(spec) -> LabeledValue:
    lines = [b for b in spec.bom if getattr(b.category, "value", b.category) == "packaging" and b.unit_cost_est is not None]
    if lines:
        total = sum(b.unit_cost_est.value * b.qty for b in lines)  # type: ignore[union-attr]
        return estimate(round(total, 2), "USD", "Sum of packaging BOM lines (" + ", ".join(b.id for b in lines) + ")")
    return estimate(DEFAULT_PACKAGING_USD, "USD", "Default retail-box + insert allowance (no packaging cost in the BOM)")



TRADEMARK_NOTE = "Trademark search needed before use."


def with_tm_note(rationale: str) -> str:
    """Every proposed name carries the trademark caveat (names are AI-generated, never cleared)."""
    r = rationale.strip().rstrip(".") + "."
    return r if TRADEMARK_NOTE.lower() in r.lower() else f"{r} {TRADEMARK_NOTE}"

@stage_handler(13)
def run_brand(ctx: StageContext) -> BrandArtifact:
    brief, spec = ctx.artifact(1), ctx.artifact(3)
    if brief is None or spec is None:
        raise ValueError("stage 13 needs the stage 1 brief and the stage 3 spec")
    log_ = AssumptionLog(13)
    price = brief.target_retail_price
    cur = price.unit
    o = spec.overall_dimensions
    prompt = render_prompt(
        "brand",
        product=brief.product_name,
        one_liner=brief.one_liner,
        category=brief.category,
        features=brief.key_features,
        markets=brief.target_markets,
        price=f"{price.value:g} {cur}",
        parts=[f"{p.name}: {p.material}, {p.finish}" for p in spec.parts],
        size=f"{o.length.value:g} x {o.width.value:g} x {o.height.value:g}",
        battery=str(bool(brief.has_battery)).lower(),
        wireless=brief.wireless or "none",
    )
    d = complete_json("fast", prompt, BrandDraft, max_tokens=3500)

    if cur == "EUR":
        usd, usd_src = round(price.value * EUR_USD, 2), f"{price.value:g} EUR × {EUR_USD} (demo EUR→USD assumption)"
    else:
        usd, usd_src = price.value, f"Founder target retail price ({cur}); no conversion applied"
    log_.add(f"Amazon price in USD: {usd_src}. Marketplace fees and VAT are not included.")
    log_.add("Name options are not trademark-searched; run a clearance search before committing.")
    log_.add("Listing copy uses only facts from the brief and spec; no certification claims until testing is complete (stage 4).")

    return BrandArtifact(
        project_id=ctx.project.id,
        generated_by=llm_tag("fast"),
        assumptions=log_.items,
        name_options=[NameOption(name=n.name.strip(), rationale=with_tm_note(n.rationale)) for n in d.name_options],
        chosen_name=None,
        packaging=PackagingSpec(
            box_type=d.box_type,
            dimensions=packaging_dimensions(spec),
            materials=d.box_materials,
            printing=d.printing,
            contents=d.contents,
            unit_cost=packaging_unit_cost(spec),
        ),
        landing_copy=LandingCopy(headline=d.headline, subheadline=d.subheadline, bullets=d.landing_bullets, cta=d.cta),
        shopify_listing=ListingDraft(
            channel="shopify", title=d.shopify.title, description=d.shopify.description, bullets=d.shopify.bullets,
            price=lv(price.value, cur, Label.estimate, "Founder target retail price (stage 1)"), keywords=d.shopify.keywords,
        ),  # fmt: skip
        amazon_listing=ListingDraft(
            channel="amazon", title=d.amazon.title, description=d.amazon.description, bullets=d.amazon.bullets,
            price=lv(usd, "USD", Label.estimate, usd_src), keywords=d.amazon.keywords,
        ),  # fmt: skip
    )
