"""Certification map (stage 4 helper called by W2). Owner: W4.

    certification_map(brief, spec) -> list[Certification]

Rule-based core (FCC 15B/15C, CE EMC / RED / LVD, UKCA, RoHS, UN38.3 + IEC 62133-2, food contact, toy safety)
+ optional LLM nuance (extra rows, marked as LLM-proposed estimates). Works without a key.
Costs and lead times are Estimates (accredited-lab ranges, demo assumptions) — never Sourced.
Citations: FCC rows quote 47 CFR Part 15 from the committed eCFR cache (data/certs/fcc_part15.json, written by _fetch_ecfr.py);
CE / UKCA / UN38.3 rows carry hand-written references (EUR-Lex, gov.uk, IATA guidance): Sourced for the citation only.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from contracts.artifacts import BriefArtifact, Certification, Label, LabeledValue, SpecArtifact
from pydantic import BaseModel, ConfigDict, Field

from api.agents._common import lv, render_prompt
from api.agents.dfm_review import has_cell, _cell_is_primary
from api.llm import complete_json

log = logging.getLogger("agents.certification")

FCC_FILE = Path(__file__).resolve().parent / "data" / "certs" / "fcc_part15.json"
# Hand-written references (citation only; costs and lead times stay Estimates). URLs checked reachable on 2026-09-26.
REF_RED = "Reference: Directive 2014/53/EU (RED), https://eur-lex.europa.eu/eli/dir/2014/53/oj"
REF_EMC = "Reference: Directive 2014/30/EU (EMC), https://eur-lex.europa.eu/eli/dir/2014/30/oj"
REF_LVD = "Reference: Directive 2014/35/EU (LVD), https://eur-lex.europa.eu/eli/dir/2014/35/oj"
REF_ROHS = "Reference: Directive 2011/65/EU (RoHS), https://eur-lex.europa.eu/eli/dir/2011/65/oj"
REF_UKCA = "Reference: UK Government guidance 'Using the UKCA marking', https://www.gov.uk/guidance/using-the-ukca-marking"
REF_UN383 = (
    "Reference: UN Manual of Tests and Criteria, section 38.3; IATA Lithium Battery Guidance Document 2026, "
    "https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf"
)

_ELECTRONIC_CATEGORIES = {"lighting", "ble_accessory", "iot_sensor", "wearable", "audio", "input_device"}
_MAINS_RE = re.compile(r"\b(mains|ac adapter|ac-dc|230\s?v|120\s?v|110\s?v|wall plug|power cord|ac power)\b", re.I)
_FOOD_RE = re.compile(r"\b(food|bowl|feeder|feeding|kitchen|drink|beverage|espresso|coffee|tea|water bottle|cup|utensil|cookware|bottle|pet dish)\b", re.I)
_KIDS_RE = re.compile(r"\b(kids?|child|children|toy|toddler|baby|infant|figurines?)\b", re.I)
_LIGHT_RE = re.compile(r"\b(led|lamp|light|lighting)\b", re.I)

MARKET_WORDS = {
    "US": ("us", "usa", "united states", "america"),
    "EU": ("eu", "europe", "european union", "germany", "france"),
    "UK": ("uk", "united kingdom", "britain", "gb"),
    "CA": ("ca", "canada"),
}


def _markets(brief: BriefArtifact) -> list[str]:
    out: list[str] = []
    for raw in brief.target_markets or ["US"]:
        low = raw.strip().lower()
        for code, words in MARKET_WORDS.items():
            if low in words or any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
                if code not in out:
                    out.append(code)
    return out or ["US"]


def _est(value: float, unit: str, why: str) -> LabeledValue:
    return lv(value, unit, Label.estimate, why)


@lru_cache(maxsize=1)
def _fcc_cache() -> dict | None:
    try:
        return json.loads(FCC_FILE.read_text())
    except (OSError, ValueError):
        return None


def fcc_cite(primary: str, *also: str) -> str:
    """Sourced rule quote of `primary` (47 CFR section number) + citations of `also`, from the eCFR cache. '' when the cache is missing."""
    d = _fcc_cache()
    if not d or primary not in d["sections"]:
        return ""
    p = d["sections"][primary]
    head = re.sub(r"^§\s*[\d.]+\s*", "", p["heading"]).rstrip(".")
    quote = p["text"][:230].rsplit(" ", 1)[0].rstrip(" ,;:")
    others = ", ".join(f"{d['sections'][n]['citation']}" for n in also if n in d["sections"])
    return (f"Sourced: {p['citation']} ({head}): “{quote}…” — eCFR text as of {d.get('text_as_of', d['fetched_on'])}, retrieved {d['fetched_on']}, {p['url']}"
            + (f". See also {others}." if others else "."))


def _cert(market: str, standard: str, because: str, cost: float, weeks: float, *, required: bool = True, note: str = "", ref: str = "") -> Certification:
    return Certification(
        market=market,
        standard=standard,
        applies_because=f"{because}. {ref}" if ref and not because.endswith(".") else (f"{because} {ref}" if ref else because),
        required=required,
        cost_est=_est(cost, "USD", f"Accredited-lab range, demo assumption{note}"),
        lead_time_weeks=_est(weeks, "weeks", "Typical lab queue + report, demo assumption"),
    )


class _ExtraDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    market: str
    standard: str
    applies_because: str
    required: bool = True
    cost_usd: float = Field(ge=0)
    lead_time_weeks: float = Field(ge=0)


class _NuanceDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    extra: list[_ExtraDraft] = Field(default_factory=list, max_length=3)
    notes: list[str] = Field(default_factory=list, max_length=3)


def rule_based(brief: BriefArtifact, spec: SpecArtifact) -> list[Certification]:
    markets = _markets(brief)
    text = " ".join([brief.prompt, brief.one_liner, spec.product_name, *brief.key_features, *brief.constraints,
                     *(p.name for p in spec.parts), *(b.part for b in spec.bom)])  # fmt: skip
    wireless = [w for w in (brief.wireless or []) if w]
    bom = list(spec.bom or [])
    battery = bool(brief.has_battery) or has_cell(bom)
    electronic = (
        bool(wireless)
        or battery
        or any(getattr(b.category, "value", b.category) == "electronic" for b in bom)
        or (brief.category in _ELECTRONIC_CATEGORIES and not re.search(r"no electronics", text, re.I))
    )
    mains = bool(_MAINS_RE.search(text))
    food = bool(_FOOD_RE.search(text))
    kids = bool(_KIDS_RE.search(text))
    radios = ", ".join(wireless)
    certs: list[Certification] = []

    if "US" in markets and electronic:
        if wireless:
            wifi5 = bool(re.search(r"wi-?fi|wlan", radios, re.I))
            certs.append(_cert("US", "FCC Part 15C (intentional radiator; 15B digital-device emissions tested with it)",
                               f"Contains an intentional radiator ({radios}); needs an FCC ID via a TCB unless a fully pre-certified module is used unmodified",
                               6000, 6, note=" — lower if a pre-certified module is integrated",
                               ref=fcc_cite("15.247", *(["15.407"] if wifi5 else []), "15.19", "15.101", "15.109")))  # fmt: skip
        else:
            certs.append(_cert("US", "FCC Part 15B (unintentional radiator)", "Digital circuitry (MCU clock, switching drivers) can emit RF noise; SDoC on a lab report", 2500, 4,
                               ref=fcc_cite("15.101", "15.107", "15.109", "15.19", "15.103")))
    if "EU" in markets and electronic:
        if wireless:
            certs.append(_cert("EU", "CE — RED 2014/53/EU (EN 300 328 / EN 301 489, EN 62368-1)", f"Radio equipment ({radios}) sold in the EU falls under the Radio Equipment Directive, which covers EMC, safety and spectrum", 7000, 6, ref=REF_RED))  # fmt: skip
        else:
            certs.append(_cert("EU", "CE — EMC 2014/30/EU (EN 55032 / EN 55035)", "Electronic product without a radio: EMC directive applies", 3000, 5, ref=REF_EMC))
            if mains:
                certs.append(_cert("EU", "CE — LVD 2014/35/EU (EN 62368-1)", "Mains-powered (50-1000 V AC) so the Low Voltage Directive applies", 2500, 4, ref=REF_LVD))
        if wireless and mains:
            certs.append(_cert("EU", "CE — LVD 2014/35/EU (EN 62368-1)", "Mains-powered product also needs LVD safety assessment", 2500, 4, ref=REF_LVD))
        if _LIGHT_RE.search(text) and electronic:
            certs.append(_cert("EU", "EN 62471 (photobiological safety of lamps)", "LED light source: photobiological risk group must be declared", 1200, 3, required=False))  # fmt: skip
        certs.append(_cert("EU", "RoHS 2011/65/EU", "Electronic product placed on the EU market must restrict hazardous substances (test report + declaration)", 600, 2, ref=REF_ROHS))
    if "UK" in markets and electronic:
        regs = "Radio Equipment Regulations 2017" if wireless else "Electromagnetic Compatibility Regulations 2016"
        certs.append(_cert("UK", f"UKCA — {regs}", "UK market needs UKCA marking (CE is not enough for Great Britain); EU test reports can usually be reused", 1500, 2, note=" — assumes CE reports reused", ref=REF_UKCA))  # fmt: skip
        certs.append(_cert("UK", "UK RoHS (SI 2012/3032)", "Electronic product placed on the UK market", 300, 1, note=" — reuses the EU RoHS report"))
    if "CA" in markets and electronic:
        std = "ISED RSS-247 / RSS-Gen (radio)" if wireless else "ICES-003 (digital device emissions)"
        certs.append(_cert("CA", std, "Canada regulates radio and digital-device emissions through ISED", 1500 if not wireless else 2500, 3, note=" — reuses FCC data"))  # fmt: skip
    if battery:
        primary = _cell_is_primary(bom)
        certs.append(_cert("Global", "UN38.3 (lithium battery transport tests)",
                           "Lithium cells must pass UN Manual of Tests and Criteria 38.3 to ship by sea/air; ask the cell supplier for the test summary", 1000, 4, ref=REF_UN383))  # fmt: skip
        if primary:
            certs.append(_cert("Global", "IEC 60086-4 (lithium primary battery safety)", "Non-rechargeable lithium cell (coin/button): IEC 60086-4 covers safety", 800, 3))
        else:
            certs.append(_cert("Global", "IEC 62133-2 (secondary lithium cell/battery safety)",
                               "Rechargeable lithium cell inside the product; also required by many retailers and by EU/UK market surveillance", 2500, 4))  # fmt: skip
    if food:
        if "US" in markets:
            certs.append(_cert("US", "FDA food-contact compliance (21 CFR 174-178)", "Parts touching food or drink must be made of FDA-compliant materials; keep supplier declarations and migration test reports", 1200, 3))  # fmt: skip
        if "EU" in markets:
            certs.append(_cert("EU", "Food-contact materials — Reg. (EC) 1935/2004 and (EU) 10/2011", "Food-contact plastics/materials need a Declaration of Compliance and migration tests", 1200, 3))  # fmt: skip
        if "UK" in markets:
            certs.append(_cert("UK", "UK food-contact materials — Reg. (EC) 1935/2004 as retained", "UK retained food-contact rules for materials touching food", 900, 3))
    if kids:
        if "US" in markets:
            certs.append(_cert("US", "CPSIA — ASTM F963 toy safety + Children's Product Certificate", "Children's product: third-party testing at a CPSC-accepted lab, lead/phthalate limits and a CPC are mandatory", 3500, 4))  # fmt: skip
        if "EU" in markets:
            certs.append(_cert("EU", "Toy Safety Directive 2009/48/EC (EN 71-1/-2/-3, EN 62115 for electric toys)", "Toy for children: mechanical, flammability and chemical tests plus CE marking", 3000, 4))  # fmt: skip
        if "UK" in markets:
            certs.append(_cert("UK", "UKCA — Toys (Safety) Regulations 2011 (EN 71)", "Toy sold in Great Britain needs UKCA marking and EN 71 testing", 1500, 3, note=" — reuses EU EN 71 report"))  # fmt: skip
    if mains and electronic and "US" in markets:
        certs.append(_cert("US", "UL/ETL listing (UL 62368-1)", "Mains-powered product: not federally mandated but required by most retailers and insurers", 4000, 6, required=False))  # fmt: skip
    if "BLE" in wireless:
        certs.append(_cert("Global", "Bluetooth SIG qualification (listing)", "Needed to use the Bluetooth name and logo; a pre-qualified module keeps the listing inexpensive", 3000, 2, required=False, note=" — verify the current SIG fee"))  # fmt: skip
    return certs


def _llm_nuance(brief: BriefArtifact, spec: SpecArtifact, existing: list[Certification]) -> list[Certification]:
    prompt = render_prompt(
        "certification",
        product=spec.product_name,
        one_liner=brief.one_liner,
        category=brief.category,
        markets=brief.target_markets,
        wireless=brief.wireless,
        battery=bool(brief.has_battery),
        features=brief.key_features,
        existing=[c.standard for c in existing],
    )
    draft = complete_json("fast", prompt, _NuanceDraft, max_tokens=1200)
    have = re.sub(r"\s+", "", " | ".join(c.standard.lower() for c in existing))
    extra: list[Certification] = []
    for e in draft.extra:
        m = re.search(r"\b(?:[a-z]{2,5}\s?)?\d[\w.\-/]*", e.standard.lower())
        key = re.sub(r"\s+", "", m.group(0) if m else " ".join(e.standard.lower().split()[:3]))
        if not key or key in have:
            continue
        extra.append(
            Certification(
                market=e.market.strip() or "Global",
                standard=e.standard.strip(),
                applies_because=e.applies_because.strip(),
                required=e.required,
                cost_est=_est(e.cost_usd, "USD", "LLM-proposed rough estimate — get a lab quote to confirm"),
                lead_time_weeks=_est(e.lead_time_weeks, "weeks", "LLM-proposed rough estimate — get a lab quote to confirm"),
            )
        )
    return extra


def certification_map(brief: BriefArtifact, spec: SpecArtifact) -> list[Certification]:
    """Certification checklist by market. Rule-based core always; LLM nuance is optional and never blocks."""
    certs = rule_based(brief, spec)
    try:
        certs += _llm_nuance(brief, spec, certs)
    except Exception as e:  # noqa: BLE001 — optional layer
        log.info("certification nuance unavailable (%s) → rule-based only", type(e).__name__)
    if not certs:
        certs.append(
            _cert("Global", "General Product Safety (GPSR 2023/988 EU; CPSA US)", "No electronics, battery, food-contact or children's-product trigger found: general product-safety duties still apply (technical file, labelling, traceability)", 500, 2)  # fmt: skip
        )
    return certs
