"""Scope gate for new prompts: is this a product the pipeline can build?

The pipeline makes small consumer products: an injection-moulded (or CNC) enclosure around a PCB/battery, about
10-400 mm, made by a contract manufacturer. A boat, a car, a house, a sofa or an app would otherwise be forced into
a generic rounded box (the "fishing boat" bug). The fast LLM judges the prompt; without it, a keyword list catches
the obvious cases. Any error lets the prompt through (the gate must never block an in-scope product).
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, ConfigDict, Field

from api.llm import LLMError, complete_json, is_configured

log = logging.getLogger("scope")

TIMEOUT_S = 8.0

# Clearly out of scope, EN + FR. Word-bounded; kept short on purpose (the LLM is the real judge).
_OUT = re.compile(
    r"\b(boats?|ships?|yachts?|kayaks?|canoes?|sailboats?|bateaux?|barques?|voiliers?|navires?|"
    r"cars?|trucks?|vans?|motorcycles?|motorbikes?|scooters?|bicycles?|bikes?|voitures?|camions?|motos?|v[ée]los?|"
    r"planes?|aircraft|airplanes?|helicopters?|avions?|h[ée]licopt[èe]res?|rockets?|fus[ée]es?|"
    r"houses?|buildings?|cabins?|sheds?|maisons?|b[âa]timents?|cabanes?|immeubles?|"
    r"sofas?|couch(es)?|beds?|wardrobes?|canap[ée]s?|lits?|armoires?|"
    r"t-?shirts?|shirts?|dress(es)?|jackets?|shoes?|sneakers?|v[êe]tements?|chaussures?|"
    r"websites?|apps?|saas|software|site web|logiciel|"
    r"recipes?|cakes?|pizzas?|recettes?|g[âa]teaux?)\b",
    re.I,
)
# Electronics words that make a keyword hit ambiguous ("bike light", "car charger", "app-controlled lamp").
_DEVICE = re.compile(
    r"\b(light|lamp|lampe|charger|chargeur|sensor|capteur|tracker|speaker|enceinte|mount|support|alarm|alarme|"
    r"remote|t[ée]l[ée]commande|gps|sonar|finder|d[ée]tecteur|detector|controller|button|bouton|monitor|device|"
    r"gadget|accessory|accessoire|bluetooth|ble|usb|led|display|[ée]cran|battery|batterie)\b",
    re.I,
)

SYSTEM = "You screen product ideas for a hardware manufacturing pipeline. Be strict about scale and category, generous about wording."

PROMPT = """PhysicalLovableX turns a one-sentence idea into a manufacturable product: a moulded or machined enclosure
(roughly 10-400 mm, handheld to desktop size) around electronics or simple mechanics, made at 500-10,000 units by a
contract manufacturer. Examples in scope: desk lamp, BLE tracker card, smart ring, pet feeder, air-quality sensor,
bike light, fish finder, bite alarm for fishing, smart speaker, remote, kitchen scale.

Out of scope: vehicles and boats, buildings, furniture, clothing and textiles, food, software-only products,
anything far larger than a desktop appliance, weapons, and anything that is not a physical product.

Founder prompt (any language): {prompt}

Return:
- in_scope: true if the prompt describes (or can reasonably be read as) a product in scope. Ambiguous → true.
- reason: when out of scope, one short sentence in the prompt's language saying why, plainly (no apology).
- suggestions: when out of scope, 2-3 in-scope products that serve the same goal, each a short prompt in the
  prompt's language the founder could send instead (e.g. for "a boat to go fishing": a sonar fish finder, a
  bite-alarm, a waterproof LED navigation light). Empty when in scope."""


class ScopeVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")
    in_scope: bool
    reason: str = ""
    suggestions: list[str] = Field(default_factory=list, max_length=4)


def _keyword_verdict(prompt: str) -> ScopeVerdict:
    if _OUT.search(prompt) and not _DEVICE.search(prompt):
        return ScopeVerdict(in_scope=False, reason="This looks larger than, or different from, a small electronic product.")
    return ScopeVerdict(in_scope=True)


def check(prompt: str) -> ScopeVerdict:
    """Judge one prompt. Never raises."""
    text = (prompt or "").strip()
    if not text:
        return ScopeVerdict(in_scope=True)
    if not is_configured("fast"):
        return _keyword_verdict(text)
    try:
        return complete_json("fast", PROMPT.format(prompt=text[:1000]), ScopeVerdict, system=SYSTEM, max_tokens=600,
                             temperature=0, timeout_s=TIMEOUT_S)
    except LLMError as e:
        log.warning("scope check fell back to keywords: %s", e)
        return _keyword_verdict(text)
    except Exception as e:  # noqa: BLE001 — the gate never blocks on its own failure
        log.warning("scope check failed open: %s", e)
        return ScopeVerdict(in_scope=True)


def message(v: ScopeVerdict) -> str:
    """User-facing refusal (shown under the prompt box)."""
    head = "PhysicalLovableX makes small physical products (a moulded case around electronics, handheld to desktop size)."
    parts = [head, v.reason.strip()] if v.reason.strip() else [head]
    if v.suggestions:
        parts.append("Try: " + " · ".join(f"“{s.strip()}”" for s in v.suggestions[:3]))
    return " ".join(parts)
