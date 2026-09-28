"""Example retrieval for codegen (C4): BM25 over the curated library, pure Python, no dependencies.

    enabled() -> bool                                    # env CODEGEN_RAG=1 (default 0: prompts unchanged)
    retrieve(query, k=4, exclude_family=None) -> [(Example, score)]
    examples_block(query, k=4, budget_chars=9000, exclude_family=None) -> str   # "" when nothing relevant

Each example is indexed as fields with weights: tags ×3, title ×2, description ×1, build123d calls in the code ×0.5
(so "sweep" or "loft" in a brief finds programs that actually call them). A small synonym table maps product words
to the library vocabulary ("housing" → enclosure, "cog" → gear). At most one seed program per family is returned,
and the family whose seed is already in the prompt is excluded.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from functools import lru_cache

from api.cad.codegen.library import Example, load_examples

K1, B = 1.4, 0.6
FIELD_WEIGHTS = {"tags": 3.0, "title": 2.0, "desc": 1.0, "code": 0.5}
MIN_SCORE = 3.0  # below this the match is noise — better no example than a misleading one
REL_SCORE = 0.35  # ... and so is anything under 35 % of the best match

_WORD = re.compile(r"[a-z][a-z0-9]+")
_STOP = set("""a an the and or of for with to in on at by from into over under is are be as it its this that these
those your our their my we you i can has have had very more most less new make made model design product concept
using use used uses into onto about like small large big mm cm top bottom side front back one two three four""".split())
# brief vocabulary -> library vocabulary (applied to queries and documents alike)
SYNONYMS = {
    "housing": "enclosure", "case": "enclosure", "casing": "enclosure", "shell": "shell", "cover": "lid",
    "cap": "cap", "cog": "gear", "sprocket": "gear", "gears": "gear", "knurled": "knurl", "knurling": "knurl",
    "grill": "grille", "grate": "grille", "vent": "vent", "vents": "vent", "ventilation": "vent", "vented": "vent",
    "louvre": "vent", "louver": "vent", "perforated": "perforated", "holes": "hole", "screw": "screw",
    "threaded": "thread", "threads": "thread", "threading": "thread", "helical": "helix", "coil": "helix",
    "hinged": "hinge", "hinges": "hinge", "pivot": "joint", "joints": "joint", "clamp": "clip", "clips": "clip",
    "snap": "snap", "latch": "latch", "curved": "curve", "curvy": "curve", "bent": "bend", "bend": "bend",
    "swept": "sweep", "sweeping": "sweep", "lofted": "loft", "lofting": "loft", "revolved": "revolve",
    "turned": "revolve", "lathe": "revolve", "filleted": "fillet", "rounded": "fillet", "chamfered": "chamfer",
    "mirrored": "mirror", "symmetric": "mirror", "symmetrical": "mirror", "array": "pattern", "patterned": "pattern",
    "grid": "grid", "radial": "polar", "circular": "polar", "bracket": "bracket", "brackets": "bracket",
    "mount": "mount", "mounting": "mount", "holder": "holder", "handles": "handle", "grip": "grip", "grips": "grip",
    "wheels": "wheel", "tyre": "tire", "tires": "tire", "fins": "fin", "blades": "blade", "propellers": "propeller",
    "props": "propeller", "gland": "gland", "cable": "cable", "cord": "cable", "door": "door", "hatch": "door",
    "compartment": "compartment", "battery": "battery", "batteries": "battery", "cells": "cell",
    "buttons": "button", "keys": "key", "keycaps": "key", "knobs": "knob", "dial": "knob", "bottle": "bottle",
    "jar": "jar", "cup": "mug", "mugs": "mug", "lampshade": "shade", "lamp": "lamp", "speaker": "speaker",
    "earbuds": "earbud", "headphones": "headphone", "ring": "ring", "rings": "ring", "phone": "smartphone",
    "drones": "drone", "quadcopter": "drone", "robotic": "robot", "vacuum": "vacuum", "legs": "leg", "chairs": "chair",
    "tables": "table", "shelves": "shelf", "pipes": "pipe", "tube": "pipe", "tubes": "pipe", "hose": "hose",
    "nozzle": "nozzle", "duct": "duct", "springs": "spring", "pulley": "pulley", "belt": "belt",
}


def enabled() -> bool:
    return os.getenv("CODEGEN_RAG", "0").strip().lower() in ("1", "true", "yes", "on")


def _stem(w: str) -> str:
    w = SYNONYMS.get(w, w)
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 4 and w.endswith("es") and w[-3] in "sxz":
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return SYNONYMS.get(w, w)


def tokens(text: str) -> list[str]:
    text = (text or "").lower().replace("_", " ").replace("-", " ")
    return [_stem(w) for w in _WORD.findall(text) if w not in _STOP]


_CALL = re.compile(r"\b([A-Za-z][A-Za-z_]+)\s*\(")


def _code_terms(code: str) -> list[str]:
    """build123d calls the program makes (loft, sweep, Helix, PolarLocations → polar locations)."""
    words = []
    for name in _CALL.findall(code):
        if name in ("build", "range", "len", "float", "int", "min", "max", "abs", "lab", "list", "sum", "round"):
            continue
        words += tokens(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name))
    return words


@lru_cache(maxsize=1)
def _index():
    docs = []
    for ex in load_examples():
        fields = {"tags": tokens(" ".join(ex.tags)), "title": tokens(ex.title), "desc": tokens(ex.description),
                  "code": _code_terms(ex.code)}
        tf: Counter = Counter()
        for f, toks in fields.items():
            for t in toks:
                tf[t] += FIELD_WEIGHTS[f]
        docs.append((ex, tf, sum(tf.values())))
    n = len(docs)
    df: Counter = Counter()
    for _, tf, _ in docs:
        df.update(tf.keys())
    idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
    avg = sum(length for *_, length in docs) / max(1, n)
    return docs, idf, avg


def reset() -> None:
    """Forget the cached index (tests / after --reindex)."""
    _index.cache_clear()


def score_all(query: str) -> list[tuple[Example, float]]:
    docs, idf, avg = _index()
    q = Counter(tokens(query))
    out = []
    for ex, tf, length in docs:
        s = 0.0
        for t, qn in q.items():
            f = tf.get(t)
            if not f:
                continue
            s += idf[t] * (f * (K1 + 1)) / (f + K1 * (1 - B + B * length / avg)) * (1 + 0.2 * (qn - 1))
        if s > 0:
            out.append((ex, s))
    return sorted(out, key=lambda x: (-x[1], x[0].id))


def retrieve(query: str, k: int = 4, exclude_family: str | None = None, min_score: float = MIN_SCORE) -> list[tuple[Example, float]]:
    picked: list[tuple[Example, float]] = []
    families: set[str] = set()
    ranked = [(ex, s) for ex, s in score_all(query)  # the seed already in the prompt / the engine's generic seed
              if ex.source != "generic" and not (ex.family and ex.family == exclude_family)]
    floor = max(min_score, REL_SCORE * ranked[0][1]) if ranked else min_score
    for ex, s in ranked:
        if s < floor or len(picked) >= k:
            break
        if ex.family and ex.family in families:
            continue  # one variant per family is enough
        picked.append((ex, s))
        if ex.family:
            families.add(ex.family)
    return picked


def examples_block(query: str, k: int = 4, budget_chars: int = 9000, exclude_family: str | None = None,
                   per_example_max: int = 4000) -> str:
    """Prompt section with the top-k relevant, sandbox-verified examples, bounded to `budget_chars`."""
    parts: list[str] = []
    used = 0
    for ex, _ in retrieve(query, k=k + 3, exclude_family=exclude_family):
        if len(parts) >= k:
            break
        code = ex.code.strip()
        if len(code) > per_example_max:
            continue
        size = f" — measured bbox {ex.bbox_mm} mm" if ex.bbox_mm else ""
        chunk = f"### {ex.id}: {ex.title}{size}\n```python\n{code}\n```\n"
        if used + len(chunk) > budget_chars:
            continue
        parts.append(chunk)
        used += len(chunk)
    if not parts:
        return ""
    return ("Reference idioms from our library of sandbox-verified build123d programs (retrieved for this brief). "
            "They run as-is in this sandbox: borrow their techniques and API usage, not their products or sizes.\n\n"
            + "\n".join(parts))


_HEAD = re.compile(r"^### ([a-z0-9_]+):", re.MULTILINE)


def last_ids(block: str) -> list[str]:
    """Example ids included in an examples_block() string (for the result metadata / benchmark)."""
    return _HEAD.findall(block or "")
