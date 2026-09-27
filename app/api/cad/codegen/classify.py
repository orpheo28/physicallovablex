"""Brief → product category → seed family (W19). Keyword rules, no LLM, deterministic.

    classify(text) -> category        # wearable | furniture_child | vacuum | home_robot | irrigation | solar_roof |
                                      # board | lighting | ble_accessory | drone | hair_dryer | camera | smartphone |
                                      # generic   (the four before generic: W21)
    seed_for(category_or_text) -> (family | None, variant | None)
"""

from __future__ import annotations

import re

CATEGORIES = ("wearable", "furniture_child", "vacuum", "home_robot", "irrigation", "solar_roof", "board", "lighting",
              "ble_accessory", "drone", "hair_dryer", "camera", "smartphone", "generic")

# ordered: the first rule with a hit wins (more specific products first)
_RULES: list[tuple[str, str]] = [
    ("generic", r"robot(ic)?[ -]?vac|robovac|robot mop"),  # a puck robot: no stick vacuum / humanoid seed fits
    ("lighting", r"ring ?light"),
    ("smartphone", r"smart ?phone|mobile phone|cell ?phone|\bphone\b|dumbphone|feature phone"),
    ("drone", r"\bdrones?\b|quadcopter|quad-?copter|multicopter|\buav\b|fpv"),
    ("hair_dryer", r"hair ?dryer|hair ?drier|blow ?dryer|hairdryer|s[eè]che-cheveux"),
    ("camera", r"\bcamera\b|instant cam|polaroid|point[- ]and[- ]shoot|\bcamcorder\b|action cam"),
    ("wearable", r"wearable|wrist ?band|smart ?band|bracelet|fitness band|smart ?ring|\bring\b|smartwatch|\bwatch\b|"
                 r"whoop|\bband\b|strap[- ]on|heart[- ]rate"),
    ("solar_roof", r"solar (array|panel|roof|farm|install)|rooftop solar|photovoltaic|\bpv\b|solar modules?"),
    ("irrigation", r"irrigat|sprinkler|drip line|watering (system|controller)|soil (moisture|probe|sensor)|"
                   r"solenoid valve|garden valve|hose (timer|valve)"),
    ("vacuum", r"vacuum|hoover|stick vac|dyson|cordless cleaner|dust ?bin"),
    ("home_robot", r"robot|humanoid|android|companion bot|\bbot\b|manipulator"),
    ("board", r"surf ?board|kite ?board|kitesurf ?board|twin[- ]tip|wake ?board|paddle ?board|\bsup\b|"
              r"body ?board|foil ?board|snowboard|skim ?board|\bsurf\b|hydrodynamic board"),
    ("furniture_child", r"changing (table|station|unit)|nursery|\bcrib\b|\bcot\b|activity table|"
                        r"kids?'? (table|desk|chair)|children'?s (table|desk|chair)|high ?chair|play ?table|"
                        r"\btable\b|\bdesk\b|\bchair\b|furniture|\bshelf\b|dresser|cabinet"),
    ("lighting", r"\blamp\b|light(ing)?\b|luminaire|lantern|sconce|\bled strip\b"),
    ("ble_accessory", r"bluetooth|\bble\b|tracker|\btag\b|beacon|key ?finder|remote|clicker|\bpuck\b"),
]
_COMPILED = [(c, re.compile(p, re.IGNORECASE)) for c, p in _RULES]
# "a bike light that pairs with your phone" is not a phone: accessory wording skips the smartphone / camera rules
_ACCESSORY = {
    "smartphone": re.compile(r"\b(to|with|via|from|on|by|for) (your|a|the|any|my) (smart ?)?phones?\b|phone (app|holder|case|"
                             r"mount|stand|charger|grip)|companion app|\bapp\b(?! ?store)", re.I),
    "camera": re.compile(r"camera (bag|strap|mount|case|lens cap)|(with|has|and) an? (small )?camera\b", re.I),
}

# category -> (family in api.cad.families | W17 family name, preset variant)
SEED: dict[str, tuple[str | None, str | None]] = {
    "wearable": ("wearable_band", None),   # W17: api/cad/build.py family 3 (in-process fallback only, no seed code)
    "furniture_child": ("furniture", "changing_table"),
    "vacuum": ("stick_vacuum", "stick"),
    "home_robot": ("home_robot", "helper"),
    "irrigation": ("irrigation", "kit"),
    "solar_roof": ("solar_array", "roof"),
    "board": ("board", "surf"),
    "lighting": (None, None),
    "ble_accessory": (None, None),
    "drone": ("drone", "follow"),
    "hair_dryer": ("hair_dryer", "pistol"),
    "camera": ("camera", "compact"),
    "smartphone": ("smartphone", "slab"),
    "generic": (None, None),
}


def classify(text: str) -> str:
    t = " ".join(str(text or "").split())
    for cat, rx in _COMPILED:
        if rx.search(t):
            if cat in _ACCESSORY and _ACCESSORY[cat].search(t):
                continue
            if cat == "furniture_child" and re.search(r"\b(lamps?|light(ing)?)\b", t, re.I) and not re.search(
                    r"changing|crib|\bcot\b|high ?chair", t, re.I):
                return "lighting"  # a desk lamp is a lamp, not a desk
            return cat
    return "generic"


def seed_for(category_or_text: str, text: str | None = None) -> tuple[str | None, str | None]:
    """(family, variant) for a category name (or a free-text brief); `text` refines the preset variant."""
    cat = category_or_text if category_or_text in SEED else classify(category_or_text)
    fam, variant = SEED[cat]
    t = f"{category_or_text} {text or ''}"
    if fam == "board" and re.search(r"kite|twin[- ]tip|wake", t, re.I) and not re.search(r"surf ?board", t, re.I):
        variant = "kite"
    if fam == "camera" and re.search(r"instant|polaroid|retro|print", t, re.I):
        variant = "instant"
    if fam == "drone" and re.search(r"mini|sub[- ]?250|249 ?g|pocket|foldable", t, re.I):
        variant = "mini"
    if fam == "hair_dryer" and re.search(r"compact|travel|mini|small", t, re.I):
        variant = "compact"
    if fam == "smartphone" and re.search(r"mini|compact|small|minimal", t, re.I):
        variant = "mini"
    if fam == "furniture" and re.search(r"activity|play ?table|kids?'? table|children'?s table", t, re.I) \
            and not re.search(r"changing", t, re.I):
        variant = "activity_table"
    return fam, variant
