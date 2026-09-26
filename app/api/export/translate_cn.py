"""Chinese text for the Factory Pack (PRD §8.1 item 8). Owner: W6.

`translate(summary_en, questions)` never raises. Order: LLM route "cn" (machine translation) → pre-translated
text (both cached examples + generic questions) → template Chinese. Everything produced here is machine-translated
and must be shown as "machine-translated — to be reviewed by a native speaker".
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

log = logging.getLogger("export.translate_cn")

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
REVIEW_NOTE = "Machine-translated — to be reviewed by a native speaker"
REVIEW_NOTE_CN = "机器翻译 — 需由母语人员审核"

SEVERITY_CN = {"critical": "严重", "major": "主要", "minor": "次要"}
MARKET_CN = {"US": "美国", "EU": "欧盟", "UK": "英国", "Global": "全球", "CA": "加拿大", "JP": "日本", "AU": "澳大利亚"}
LABEL_CN = {"measured": "实测", "sourced": "有来源", "estimate": "估算", "fictional": "虚构—演示数据"}


class _Translation(BaseModel):
    summary_cn: str
    questions_cn: list[str] = Field(default_factory=list)  # missing/short list → per-question fallback


@lru_cache(maxsize=1)
def known_translations() -> dict[str, str]:
    """EN → CN pairs from the cached examples' Factory Packs (hand-translated fixtures)."""
    pairs: dict[str, str] = {}
    for path in sorted(FIXTURES_DIR.glob("*/factory_pack.json")):
        try:
            raw = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            continue
        if raw.get("product_summary") and raw.get("product_summary_cn"):
            pairs[raw["product_summary"].strip()] = raw["product_summary_cn"]
        for q in raw.get("questions", []):
            if q.get("en") and q.get("cn"):
                pairs[q["en"].strip()] = q["cn"]
    return pairs


def template_summary_cn(product_name: str, markets: list[str], quantities: list[int]) -> str:
    mk = "、".join(MARKET_CN.get(m, m) for m in markets) or "待定"
    qty = "、".join(f"{q:,}" for q in quantities) or "待定"
    return f"产品：{product_name}（名称保留英文）。目标市场：{mk}。目标数量：{qty} 件。详细规格、BOM、DFM 与认证清单见本资料包各章节（英文原文）。"


def _llm(summary_en: str, en_questions: list[str]) -> tuple[str, list[str], str]:
    from api import llm

    prompt = (
        "Translate into Simplified Chinese for a Chinese factory (professional manufacturing terminology). "
        "Keep part numbers, standards (FCC, UN38.3, IEC...), units and numbers unchanged.\n"
        f"summary_en: {json.dumps(summary_en, ensure_ascii=False)}\n"
        f"questions_en: {json.dumps(en_questions, ensure_ascii=False)}\n"
        "Return summary_cn and questions_cn (same order and length as questions_en)."
    )
    out = llm.complete_json("cn", prompt, _Translation, system="You are a professional EN→ZH technical translator for hardware manufacturing.",
                            timeout_s=20)  # optional layer on the wow-screen path: slow provider → pre-translated fallback
    if not out.summary_cn.strip():
        raise ValueError("empty CN summary")
    qs: list[str | None] = [q.strip() or None for q in out.questions_cn[: len(en_questions)]]
    if len(qs) != len(en_questions):  # model merged/dropped a question: keep the ones we can trust by position only if none are missing
        log.info("CN translation returned %d questions for %d; per-question fallback", len(out.questions_cn), len(en_questions))
        qs = [None] * len(en_questions)
    return out.summary_cn.strip(), qs, f"llm:{llm.model_for('cn')}"


def translate(summary_en: str, product_name: str, markets: list[str], quantities: list[int], questions: list[tuple[str, str | None]]) -> tuple[str, list[str | None], str]:
    """questions = [(en, cn_fallback | None)]. Returns (summary_cn, [cn or None], source) where source is
    'llm:<model>' or 'fallback'."""
    en_list = [q[0] for q in questions]
    try:
        s, qs, src = _llm(summary_en, en_list)
        if all(q is not None for q in qs):
            return s, list(qs), src
        known = known_translations()
        return s, [q or known.get(en.strip()) or fb for q, (en, fb) in zip(qs, questions)], src
    except Exception as e:  # noqa: BLE001 — LLMNotConfigured, LLMError, validation, anything
        log.info("CN translation via LLM unavailable (%s) → pre-translated fallback", type(e).__name__)
    known = known_translations()
    summary_cn = known.get(summary_en.strip()) or template_summary_cn(product_name, markets, quantities)
    out: list[str | None] = []
    for en, fb in questions:
        out.append(known.get(en.strip()) or fb)
    return summary_cn, out, "fallback"
