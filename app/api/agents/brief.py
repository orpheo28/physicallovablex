"""Stage 1 — Brief (spec copilot). Owner: W4.

Two modes: idea (prompt only) and prototype (prompt + pasted BOM, parsed here in code). The LLM proposes the
brief and up to 5 clarifying questions with defaults; Python applies the answers (ctx.inputs["answers"]) and
guarantees the contract (question ids, defaults, price label, volume tiers).
"""

from __future__ import annotations

import re
from typing import Literal

from contracts.artifacts import (
    BOMCategory,
    BOMItem,
    BriefArtifact,
    ClarifyingQuestion,
    Label,
    LabeledValue,
    ProjectMode,
)
from pydantic import BaseModel, ConfigDict, Field

from api.agents._common import CATEGORIES, AssumptionLog, llm_tag, lv, render_prompt
from api.llm import complete_json
from api.stages.registry import StageContext, stage_handler

DEFAULT_VOLUMES = [500, 2000, 10000]
TOPICS = ("markets", "volume", "target_price", "battery", "wireless")
CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}
KNOWN_MARKETS = {"US": ("us", "usa", "united states", "america"), "EU": ("eu", "europe", "european"),
                 "UK": ("uk", "united kingdom", "britain"), "CA": ("ca", "canada"), "AU": ("au", "australia")}  # fmt: skip
KNOWN_WIRELESS = {"BLE": ("ble", "bluetooth"), "Wi-Fi": ("wi-fi", "wifi", "wlan"), "NFC": ("nfc",),
                  "Zigbee": ("zigbee",), "LoRa": ("lora",), "Cellular": ("cellular", "lte", "4g", "5g")}  # fmt: skip


class _Draft(BaseModel):
    model_config = ConfigDict(extra="ignore")


class QuestionDraft(_Draft):
    id: str = ""
    topic: Literal["markets", "volume", "target_price", "battery", "wireless", "other"]
    question: str
    options: list[str] = Field(default_factory=list)
    default: str = ""


class BriefDraft(_Draft):
    product_name: str
    one_liner: str
    category: Literal[CATEGORIES]  # type: ignore[valid-type]
    target_markets: list[str] = Field(default_factory=lambda: ["US"])
    target_price_value: float = Field(gt=0)
    target_price_currency: Literal["USD", "EUR", "GBP"] = "USD"
    price_from_prompt: bool = False
    key_features: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    has_battery: bool = False
    wireless: list[str] = Field(default_factory=list)
    questions: list[QuestionDraft] = Field(default_factory=list, max_length=8)


# --------------------------------------------------------------------------- prototype mode: BOM parser

_PACKAGING = re.compile(r"\b(box|carton|packag\w*|sleeve|insert|manual|label|bag|blister|wrap)\b", re.I)
_ELECTRONIC = re.compile(
    r"\b(led|ic|mcu|soc|resistor|capacitor|inductor|diode|mosfet|transistor|pcb|pcba|fpc|usb|battery|cell|li-?ion|li-?po|"
    r"18650|cr20\d\d|sensor|module|connector|antenna|crystal|oscillator|nrf\d*\w*|esp32\w*|stm32\w*|ble|charger|"
    r"regulator|ldo|buck|boost|accelerometer|imu|nfc|speaker|microphone|display|e-?ink|switch|button|buzzer|motor|afe|ppg|pmic|"
    r"modem|lte|wi-?fi|bluetooth|photodiode|emitter|dram|lpddr\w*|emmc|flash)\b",
    re.I,
)
_HEADER = re.compile(r"\b(part|item|component|description|name)\b", re.I)
_QTY_HEADER = re.compile(r"^(qty|quantity|count|q)$", re.I)
_MPN_HEADER = re.compile(r"^(mpn|manufacturer[_ ]?p(art)?[_ ]?n(umber)?|pn|part[_ ]?number)$", re.I)
_PRICE_HEADER = re.compile(r"price|cost|usd|\$", re.I)
_PRICE_CELL = re.compile(r"^\$?\s*(\d+(?:\.\d+)?)\s*(?:usd|\$)?$", re.I)
_LCSC = re.compile(r"^C\d{4,9}$")
_QTY_CELL = re.compile(r"^(?:x\s*)?(\d+(?:\.\d+)?)(?:\s*x|\s*pcs?)?$", re.I)


def _looks_like_mpn(cell: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-_/.]{4,}", cell)) and any(c.isdigit() for c in cell) and " " not in cell


def _classify(text: str) -> BOMCategory:
    if _PACKAGING.search(text):
        return BOMCategory.packaging
    if _ELECTRONIC.search(text):
        return BOMCategory.electronic
    return BOMCategory.mechanical


def parse_pasted_bom(text: str | None) -> list[BOMItem]:
    """Deterministic parser for a pasted BOM (CSV / TSV / ; / | / free text lines). Never raises on odd lines."""
    if not text or not text.strip():
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith(("#", "//"))]
    if not lines:
        return []
    delim = max("\t;|,", key=lambda d: lines[0].count(d))
    delim = delim if lines[0].count(delim) else None
    header: list[str] | None = None
    if delim:
        first = [c.strip() for c in lines[0].split(delim)]
        if _HEADER.search(lines[0]) and not any(_QTY_CELL.match(c) for c in first):
            header = first
            lines = lines[1:]
    counters = {BOMCategory.electronic: 0, BOMCategory.mechanical: 0, BOMCategory.packaging: 0}
    prefix = {BOMCategory.electronic: "e", BOMCategory.mechanical: "m", BOMCategory.packaging: "k"}
    items: list[BOMItem] = []
    for ln in lines:
        cells = [c.strip() for c in ln.split(delim)] if delim else [ln]
        cells = [c for c in cells if c]
        if not cells:
            continue
        part = mpn = None
        qty = price = None
        if header:
            for h, c in zip(header, [c.strip() for c in ln.split(delim)]):
                if _QTY_HEADER.match(h) and (m := _QTY_CELL.match(c)):
                    qty = float(m.group(1))
                elif _PRICE_HEADER.search(h) and (m := _PRICE_CELL.match(c)):
                    price = float(m.group(1))
                    cells = [x for x in cells if x != c]
                elif _MPN_HEADER.match(h) and c:
                    mpn = c
                elif _HEADER.search(h) and part is None and c:
                    part = c
        if part is None:
            rest = []
            for c in cells:
                if qty is None and (m := _QTY_CELL.match(c)):
                    qty = float(m.group(1))
                else:
                    rest.append(c)
            if not delim and qty is None:  # free text: "2x LED 2835" or "LED 2835 x2"
                m = re.match(r"^(\d+)\s*[x×]\s*(.+)$", ln, re.I) or re.match(r"^(.+?)\s*[x×]\s*(\d+)$", ln, re.I)
                if m:
                    a, b = m.group(1), m.group(2)
                    qty, rest = (float(a), [b]) if a.isdigit() else (float(b), [a])
            if mpn is None:
                for c in rest[1:]:
                    if _looks_like_mpn(c):
                        mpn = c
                        rest.remove(c)
                        break
            part = rest[0] if rest else cells[0]
        desc = " ".join(c for c in cells if c not in (part, mpn) and not _QTY_CELL.match(c)) or None
        cat = _classify(f"{part} {desc or ''}")
        counters[cat] += 1
        items.append(
            BOMItem(
                id=f"{prefix[cat]}{counters[cat]}",
                part=part[:120],
                category=cat,
                qty=qty if qty and qty > 0 else 1.0,
                description=desc[:200] if desc else None,
                manufacturer_pn=mpn if mpn and not _LCSC.match(mpn) else None,
                lcsc_pn=mpn if mpn and _LCSC.match(mpn) else None,
                unit_cost_est=LabeledValue(value=price, unit="USD", label="estimate",
                                           source_or_assumption="Unit price from the founder's pasted prototype BOM") if price else None,
            )
        )
    return items


# --------------------------------------------------------------------------- answers → fields


def _parse_markets(answer: str) -> list[str]:
    low = answer.lower()
    out = [code for code, words in KNOWN_MARKETS.items() if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)]
    return out


def _parse_volume(answer: str) -> int | None:
    m = re.search(r"(\d[\d,. ]*)\s*(k)?\b", answer.lower())
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", "").replace(" ", ""))
    except ValueError:
        return None
    return int(num * 1000) if m.group(2) else int(num)


def _parse_price(answer: str) -> tuple[float, str | None] | None:
    m = re.search(r"([€$£]|USD|EUR|GBP)?\s*(\d+(?:[.,]\d+)?)\s*([€$£]|USD|EUR|GBP)?", answer, re.I)
    if not m:
        return None
    cur = m.group(1) or m.group(3)
    code = CURRENCY_SYMBOLS.get(cur, cur.upper() if cur else None)
    return float(m.group(2).replace(",", ".")), code


def _parse_wireless(answer: str) -> list[str]:
    low = answer.lower()
    if re.fullmatch(r"\s*(none|no|n/a|nothing)\W*", low):
        return []
    return [name for name, words in KNOWN_WIRELESS.items() if any(w in low for w in words)]


def _parse_battery(answer: str) -> bool:
    return not re.match(r"\s*(none|no|n/a|not|without|mains|usb only)\b", answer.lower())


_TEMPLATES = {
    "markets": ("Which markets at launch?", ["US", "EU", "UK", "US + EU"]),
    "volume": ("First production run size?", ["500", "2,000", "10,000"]),
    "target_price": ("Confirm the target retail price?", []),
    "battery": ("Does it need a battery, and what runtime?", ["None (mains/USB)", "Rechargeable Li-ion", "Coin cell"]),
    "wireless": ("Any app or wireless control?", ["None", "BLE", "Wi-Fi", "NFC"]),
}


def _build_questions(draft: BriefDraft, default_answers: dict[str, str]) -> list[ClarifyingQuestion]:
    picked: dict[str, QuestionDraft] = {}
    for q in draft.questions:
        if q.topic in TOPICS and q.topic not in picked:
            picked[q.topic] = q
    questions: list[ClarifyingQuestion] = []
    for topic in TOPICS:
        q = picked.get(topic)
        if q is None and len(picked) >= 5:
            continue
        text, options = (q.question, list(q.options)) if q else _TEMPLATES[topic]
        default = (q.default.strip() if q and q.default.strip() else default_answers[topic])
        if default and default not in options and topic != "target_price":
            options = [*options, default]
        questions.append(ClarifyingQuestion(id="", topic=topic, question=text, options=options[:5], answer=default))  # type: ignore[arg-type]
    for i, q in enumerate(questions[:5], 1):
        q.id = f"q{i}"
    return questions[:5]


def _answer_for(q: ClarifyingQuestion, answers: dict) -> str | None:
    for key in (q.id, q.topic):
        val = answers.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


@stage_handler(1)
def run_brief(ctx: StageContext) -> BriefArtifact:
    project = ctx.project
    answers: dict = dict((ctx.inputs or {}).get("answers") or {})
    bom = parse_pasted_bom(project.pasted_bom) if project.pasted_bom else []
    log = AssumptionLog(1)

    prompt = render_prompt(
        "brief",
        mode=str(getattr(project.mode, "value", project.mode)),
        prompt=project.prompt,
        name=project.name,
        bom=[b.model_dump(mode="json", include={"id", "part", "category", "qty", "manufacturer_pn"}) for b in bom],
        answers=answers,
    )
    draft = complete_json("main", prompt, BriefDraft)

    markets = [m.strip() for m in draft.target_markets if m.strip()] or ["US"]
    volumes = list(DEFAULT_VOLUMES)
    price_value, price_cur = draft.target_price_value, draft.target_price_currency
    price_src = (
        "Founder target retail price stated in the prompt"
        if draft.price_from_prompt
        else "Assumed by the spec copilot from category comparables — confirm with the founder"
    )
    has_battery, wireless = draft.has_battery, list(draft.wireless)

    default_answers = {
        "markets": " + ".join(markets),
        "volume": f"{volumes[1]:,}",
        "target_price": f"{price_value:g} {price_cur}",
        "battery": "Rechargeable Li-ion" if has_battery else "None (mains/USB)",
        "wireless": ", ".join(wireless) if wireless else "None",
    }
    questions = _build_questions(draft, default_answers)

    defaulted: list[str] = []
    for q in questions:
        given = _answer_for(q, answers)
        value = given if given is not None else (q.answer or default_answers[q.topic])
        if given is None:
            defaulted.append(f"{q.topic}={value}")
        q.answer, q.skipped = value, given is None
        if given is None:
            continue
        if q.topic == "markets" and (parsed := _parse_markets(value)):
            markets = parsed
        elif q.topic == "volume" and (vol := _parse_volume(value)):
            if vol not in volumes:
                volumes = sorted({*volumes, vol})
        elif q.topic == "target_price" and (parsed_price := _parse_price(value)):
            price_value = parsed_price[0]
            price_cur = parsed_price[1] if parsed_price[1] in ("USD", "EUR", "GBP") else price_cur
            price_src = f"Founder answer to {q.id}"
        elif q.topic == "battery":
            has_battery = _parse_battery(value)
        elif q.topic == "wireless":
            wireless = _parse_wireless(value)

    if defaulted:
        log.add("Skipped clarifying questions use their defaults: " + "; ".join(defaulted) + ". Re-run stage 1 with answers to change them.")
    if not draft.price_from_prompt and not any(q.topic == "target_price" and not q.skipped for q in questions):
        log.add("Target retail price proposed by the spec copilot (not stated by the founder); confirm before costing.")
    if project.mode in (ProjectMode.prototype, ProjectMode.prototype.value) and not bom:
        log.add("Prototype mode without a parsable pasted BOM: the BOM will be proposed at stage 3.")
    if bom:
        log.add("Pasted BOM parsed by rule (columns guessed by header/position); parts classified by keyword; costs are matched at stage 5.")

    return BriefArtifact(
        project_id=project.id,
        generated_by=llm_tag("main"),
        assumptions=log.items,
        mode=project.mode,
        prompt=project.prompt,
        product_name=draft.product_name.strip() or project.name,
        one_liner=draft.one_liner.strip(),
        category=draft.category,
        target_markets=markets,
        target_retail_price=lv(price_value, price_cur, Label.estimate, price_src),
        target_volumes=volumes,
        key_features=draft.key_features,
        constraints=draft.constraints,
        has_battery=has_battery,
        wireless=wireless,
        pasted_bom=bom,
        clarifying_questions=questions,
    )
