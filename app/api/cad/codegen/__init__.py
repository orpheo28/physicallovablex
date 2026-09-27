"""Text-to-CAD engine (W19): the AI writes build123d code, we run it in a sandbox, measure it, and self-repair.

    from api.cad.codegen import generate_cad, refine_cad, classify, seed_for, LABEL
"""

from api.cad.codegen.classify import CATEGORIES, classify, seed_for
from api.cad.codegen.engine import FALLBACK_LABEL, LABEL, generate_cad, latest_version, refine_cad
from api.cad.codegen.sandbox import check_code, run_code

__all__ = ["generate_cad", "refine_cad", "latest_version", "classify", "seed_for", "CATEGORIES", "LABEL",
           "FALLBACK_LABEL", "check_code", "run_code"]
