"""Launch Dossier PDF (PRD §8 "Final export"). Owner: W6.

`@provider("export_pdf")`: ctx → PDF bytes (ReportLab platypus). Order: cover · Factory Pack (EN) · Factory Pack (CN,
STSong-Light CID font) · the 13 stage outputs · assumption register · label legend.

Honesty rules enforced here:
- every LabeledValue is printed as "value unit [Label]" (Measured / Sourced / Estimate / Fictional — demo data);
- factory / quote / freight pages carry a "Fictional — demo data" banner;
- a stage with fallback=true (or not run) carries a "Cached example" note.
A stage that cannot be rendered never breaks the dossier: it falls back to a generic dump, then to a note.
"""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable
from xml.sax.saxutils import escape

from contracts.artifacts import CACHED_NOTE, STAGE_NAMES, STAGE_TITLES, Assumption, LabeledValue, process_label
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from api.export import translate_cn as cn
from api.stages.registry import StageContext, provider

log = logging.getLogger("export.pdf")

CJK_FONT = "STSong-Light"
try:
    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
except Exception:  # noqa: BLE001 — already registered
    pass

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

LABEL_TEXT = {"measured": "Measured", "sourced": "Sourced", "estimate": "Estimate", "fictional": "Fictional — demo data"}
LABEL_COLOR = {"measured": "#0b7a3b", "sourced": "#1d4ed8", "estimate": "#b45309", "fictional": "#b91c1c"}
FICTIONAL_BANNER = "Fictional — demo data: factories, capacity, quotes, negotiation and freight rates on this page are simulated."

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#d1d5db")
HEAD_BG = colors.HexColor("#f3f4f6")
ACCENT = colors.HexColor("#111827")

# ---------------------------------------------------------------------------- text helpers

_CJK = re.compile(r"([⺀-鿿豈-﫿＀-￯　-〿]+)")
_REPL = {
    "→": "->", "←": "<-", "≤": "<=", "≥": ">=", "≈": "~", "−": "-", "‑": "-", "≠": "!=", "Δ": "delta ", "Ω": "ohm ",
    "✓": "yes", "⚠": "!", "µ": "µ", " ": " ", "​": "", " ": " ", " ": " ", "√": "sqrt", "∞": "inf",
    "²": "2", "³": "3", "¹": "1",
}


def _latin(seg: str) -> str:
    out = []
    for ch in seg:
        ch = _REPL.get(ch, ch)
        for c in ch:
            try:
                c.encode("cp1252")
                out.append(c)
            except UnicodeEncodeError:
                out.append("?")
    return "".join(out)


def mixed(text: Any) -> str:
    """Escape for Paragraph markup; CJK runs use the CID font, everything else stays in Helvetica."""
    s = "" if text is None else str(text)
    parts = _CJK.split(s)
    out = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2:
            out.append(f'<font name="{CJK_FONT}">{escape(part)}</font>')
        else:
            out.append(escape(_latin(part)).replace("\n", "<br/>"))
    return "".join(out)


def num(v: float) -> str:
    v = float(v)
    if abs(v - round(v)) < 1e-9 and abs(v) < 1e15:
        return f"{int(round(v)):,}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def chip(label: str, bilingual: bool = False) -> str:
    label = getattr(label, "value", label)
    txt = LABEL_TEXT.get(label, str(label))
    if bilingual:
        txt = f"{txt} {cn.LABEL_CN.get(label, '')}"
    return f'<font color="{LABEL_COLOR.get(label, "#374151")}" size="6.5"><b>[{mixed(txt)}]</b></font>'


def lvs(v: LabeledValue | None, bilingual: bool = False) -> str:
    """Markup for one labeled value: '1.5745 USD [Sourced]'."""
    if v is None:
        return "—"
    return f"{mixed(num(v.value))} {mixed(v.unit)} {chip(v.label, bilingual)}"


def lv_src(v: LabeledValue | None) -> str:
    """Labeled value + its source/assumption in small grey (for tables where the source matters)."""
    if v is None:
        return "—"
    return f'{lvs(v)}<br/><font size="6" color="#6b7280">{mixed(v.source_or_assumption)}</font>'


def dims_str(d: Any) -> str:
    vals = [d.length, d.width, d.height]
    labels = {v.label for v in vals}
    unit = vals[0].unit
    body = " × ".join(num(v.value) for v in vals) + f" {unit}"
    if len(labels) == 1:
        return f"{mixed(body)} {chip(vals[0].label)}"
    return " × ".join(f"{mixed(num(v.value))} {chip(v.label)}" for v in vals) + f" {mixed(unit)}"


# ---------------------------------------------------------------------------- styles

_base = getSampleStyleSheet()


def _style(name: str, **kw: Any) -> ParagraphStyle:
    return ParagraphStyle(name, parent=_base["Normal"], **kw)


ST = {
    "body": _style("body", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK, alignment=TA_LEFT),
    "small": _style("small", fontName="Helvetica", fontSize=7.5, leading=10, textColor=INK),
    "cell": _style("cell", fontName="Helvetica", fontSize=7.5, leading=9.6, textColor=INK),
    "cellh": _style("cellh", fontName="Helvetica-Bold", fontSize=7.5, leading=9.6, textColor=INK),
    "muted": _style("muted", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED),
    "h1": _style("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=INK, spaceBefore=0, spaceAfter=6),
    "h2": _style("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=9, spaceAfter=3),
    "banner_red": _style("banner_red", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#991b1b"), backColor=colors.HexColor("#fee2e2"), borderPadding=(5, 6, 5, 6), spaceAfter=8),
    "banner_amber": _style("banner_amber", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#92400e"), backColor=colors.HexColor("#fef3c7"), borderPadding=(5, 6, 5, 6), spaceAfter=8),
    "banner_blue": _style("banner_blue", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#1e3a8a"), backColor=colors.HexColor("#dbeafe"), borderPadding=(5, 6, 5, 6), spaceAfter=8),
    "title": _style("title", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=INK, spaceAfter=4),
    "subtitle": _style("subtitle", fontName="Helvetica", fontSize=13, leading=17, textColor=MUTED, spaceAfter=10),
}


class Heading(Paragraph):
    """Paragraph that registers a PDF bookmark/outline entry."""

    def __init__(self, text: str, style: ParagraphStyle, outline: str | None = None, level: int = 0):
        super().__init__(text, style)
        self.outline = outline
        self.level = level


class Doc(SimpleDocTemplate):
    def __init__(self, buf: io.BytesIO, footer_text: str, **kw: Any):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=18 * mm, **kw)
        self.footer_text = footer_text
        self._seq = 0

    def afterFlowable(self, flowable: Any) -> None:
        if isinstance(flowable, Heading) and flowable.outline:
            self._seq += 1
            key = f"bm{self._seq}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.outline, key, level=flowable.level, closed=False)

    def on_page(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 10 * mm, self.footer_text)
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
        canvas.restoreState()


def P(text: Any, style: str = "body") -> Paragraph:
    return Paragraph(mixed(text), ST[style])


def M(markup: str, style: str = "body") -> Paragraph:
    """Paragraph from already-escaped markup."""
    return Paragraph(markup, ST[style])


def bullets(items: list[Any], style: str = "body") -> list[Paragraph]:
    return [Paragraph("• " + mixed(i), ST[style]) for i in items]


def table(header: list[str], rows: list[list[Any]], widths: list[float], markup: bool = True) -> Table:
    """Table with wrapped cells. Cell values: str already marked up if markup=True, else plain text."""
    def cell(v: Any, style: str) -> Paragraph:
        text = "" if v is None else str(v)
        return Paragraph(text if markup else mixed(text), ST[style])

    data = [[Paragraph(mixed(h), ST["cellh"]) for h in header]] + [[cell(c, "cell") for c in r] for r in rows]
    t = Table(data, colWidths=[w * CONTENT_W for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def kv(rows: list[tuple[str, str]], widths: tuple[float, float] = (0.24, 0.76)) -> Table:
    """Key/value table; values are markup."""
    data = [[Paragraph(mixed(k), ST["cellh"]), Paragraph(v, ST["cell"])] for k, v in rows]
    t = Table(data, colWidths=[w * CONTENT_W for w in widths])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def h1(text: str, outline: str | None = None, level: int = 0) -> Heading:
    return Heading(mixed(text), ST["h1"], outline=outline or text, level=level)


def h2(text: str) -> Paragraph:
    return P(text, "h2")


def sp(h: float = 4) -> Spacer:
    return Spacer(1, h)


# ---------------------------------------------------------------------------- Factory Pack (EN / CN)


def _risk_str(item: Any) -> str:
    if not item.risk:
        return "—"
    txt = f"<b>{mixed(item.risk.level)}</b>"
    if item.risk.reasons:
        txt += ": " + mixed("; ".join(item.risk.reasons))
    return txt


def factory_pack_en(fp: Any) -> list[Any]:
    f: list[Any] = [h1("Factory Pack (EN)", "Factory Pack EN - English", 0)]
    f.append(P(f"{fp.product_name} · pack {fp.id} · version {fp.version} · project {fp.project_id}", "muted"))
    f.append(sp(7))
    if getattr(fp, "cached_note", None):
        stages = ", ".join(str(n) for n in getattr(fp, "fallback_stages", []) or [])
        f.append(M(mixed(f"{fp.cached_note}" + (f" (stages {stages})." if stages else ".")), "banner_amber"))
    elif fp.fallback:
        f.append(M(mixed("Cached example — at least one section of this pack comes from a pre-built example, not from this project's live stages."), "banner_amber"))
    f.append(sp(4))
    f += [h2("1. Product summary and target markets"), P(fp.product_summary), P("Target markets: " + ", ".join(fp.target_markets), "small")]
    s = fp.spec
    f += [h2("2. Structured spec")]
    f.append(kv([("Overall dimensions", dims_str(s.overall_dimensions)), ("Weight", lvs(s.weight)), ("Tolerances", mixed("; ".join(s.tolerances)) or "—")]))
    f.append(sp(4))
    f.append(table(
        ["Part", "Material", "Finish", "Process", "Tolerance", "Dimensions", "Wall"],
        [[mixed(p.name), mixed(p.material), mixed(p.finish), mixed(process_label(p.process_hint) if p.process_hint else "—"), mixed(p.tolerance or "—"), dims_str(p.dimensions) if p.dimensions else "—", lvs(p.wall_thickness) if p.wall_thickness else "—"] for p in s.parts],
        [0.14, 0.15, 0.13, 0.1, 0.16, 0.19, 0.13],
    ))
    f += [h2("3. CAD (STEP) and drawings")]
    f += bullets([f"{c.format.upper()} — {c.url}" + (f" ({c.description})" if c.description else "") for c in fp.cad_files], "small") or [P("—")]
    f += [h2("4. BOM with component risk and alternatives")]
    f.append(table(
        ["Part", "Qty", "Unit cost", "LCSC", "Risk", "Alternative"],
        [[mixed(b.part), num(b.qty), lvs(b.unit_cost_est) if b.unit_cost_est else "—", mixed(b.lcsc_pn or "—"), _risk_str(b), mixed(b.alternative or "—")] for b in fp.bom],
        [0.24, 0.05, 0.17, 0.09, 0.25, 0.20],
    ))
    f += [h2("5. DFM alerts and resolutions")]
    f.append(table(
        ["#", "Severity", "Method", "Alert", "Fix / resolution", "Rule"],
        [[mixed(i.id), mixed(i.severity), "Measured (CAD)" if i.method == "measured" else "AI-reviewed", mixed(i.description) + (f"<br/>{lvs(i.measurement)}" if i.measurement else ""), mixed(i.fix) + (f"<br/><i>Resolved: {mixed(i.resolution)}</i>" if i.resolved and i.resolution else ""), mixed(i.rule_citation)] for i in fp.dfm_alerts],
        [0.04, 0.09, 0.1, 0.27, 0.27, 0.23],
    ))
    f += [h2("6. Certification checklist by market")]
    f.append(table(
        ["Market", "Standard", "Why", "Required", "Cost", "Lead time"],
        [[mixed(c.market), mixed(c.standard), mixed(c.applies_because), "Yes" if c.required else "Check", lvs(c.cost_est), lvs(c.lead_time_weeks)] for c in fp.certifications],
        [0.08, 0.26, 0.24, 0.09, 0.17, 0.16],
    ))
    f += [h2("7. Target quantities and cost estimate")]
    f.append(P("Target quantities: " + " / ".join(f"{q:,}" for q in fp.target_quantities) + " units", "small"))
    f.append(table(
        ["Qty", "BOM", "Assembly", "Packaging", "Unit cost (ex-works)", "Tooling / unit", "Margin"],
        [[num(t.quantity), lvs(t.bom_cost), lvs(t.assembly_cost), lvs(t.packaging_cost), lvs(t.unit_cost), lvs(t.tooling_amortisation), lvs(t.margin_pct)] for t in fp.cost_estimate],
        [0.07, 0.14, 0.14, 0.14, 0.17, 0.17, 0.17],
    ))
    f += [h2("8. Questions for the factory (EN + CN)")]
    f.append(P("Chinese text is machine-translated — to be reviewed by a native speaker.", "muted"))
    f.append(table(["#", "English", "中文 (machine-translated)"], [[mixed(q.id), mixed(q.en), mixed(q.cn or "—")] for q in fp.questions], [0.06, 0.47, 0.47]))
    f += [h2("9. Assumption register"), P("The full register is printed at the end of this dossier (" + str(len(fp.assumption_register)) + " entries).", "small")]
    return f


def factory_pack_cn(fp: Any) -> list[Any]:
    """Chinese section: headings, summary and questions in Chinese; technical tables keep their English content."""
    b = True  # bilingual chips
    f: list[Any] = [PageBreak(), h1("工厂资料包（中文版）", "Factory Pack CN - Chinese, machine-translated", 0)]
    f.append(P(f"{fp.product_name} · {fp.id} · 版本 {fp.version}", "muted"))
    f.append(sp(8))
    f.append(M(mixed(f"{cn.REVIEW_NOTE_CN}。 {cn.REVIEW_NOTE}. 技术参数表保留英文原文，数值均标注来源标签。"), "banner_amber"))
    f += [h2("1. 产品摘要与目标市场"), P(fp.product_summary_cn or cn.template_summary_cn(fp.product_name, fp.target_markets, fp.target_quantities))]
    f.append(P("目标市场：" + "、".join(cn.MARKET_CN.get(m, m) for m in fp.target_markets), "small"))
    s = fp.spec
    f += [h2("2. 结构化规格")]
    f.append(kv([("外形尺寸（长×宽×高）", dims_str(s.overall_dimensions)), ("重量", lvs(s.weight, b)), ("公差", mixed("; ".join(s.tolerances)) or "—")]))
    f += [h2("3. 三维模型 (STEP) 与图纸")]
    f += bullets([f"{c.format.upper()} — {c.url}" for c in fp.cad_files], "small") or [P("—")]
    f += [h2("4. 物料清单 (BOM) 与风险")]
    f.append(table(
        ["零件", "数量", "单价", "风险"],
        [[mixed(x.part), num(x.qty), lvs(x.unit_cost_est, b) if x.unit_cost_est else "—", _risk_str(x)] for x in fp.bom],
        [0.36, 0.07, 0.24, 0.33],
    ))
    f += [h2("5. DFM（可制造性设计）提示")]
    f.append(table(
        ["编号", "严重程度", "问题（英文原文）", "建议修改"],
        [[mixed(i.id), mixed(cn.SEVERITY_CN.get(i.severity, i.severity)), mixed(i.description), mixed(i.fix)] for i in fp.dfm_alerts],
        [0.06, 0.1, 0.42, 0.42],
    ))
    f += [h2("6. 认证清单")]
    f.append(table(
        ["市场", "标准", "费用", "周期"],
        [[mixed(cn.MARKET_CN.get(c.market, c.market)), mixed(c.standard), lvs(c.cost_est, b), lvs(c.lead_time_weeks, b)] for c in fp.certifications],
        [0.1, 0.4, 0.26, 0.24],
    ))
    f += [h2("7. 目标数量与成本估算")]
    f.append(P("目标数量：" + " / ".join(f"{q:,}" for q in fp.target_quantities) + " 件", "small"))
    f.append(table(
        ["数量", "出厂单价（不含税）", "模具摊销/件", "毛利率"],
        [[num(t.quantity), lvs(t.unit_cost, b), lvs(t.tooling_amortisation, b), lvs(t.margin_pct, b)] for t in fp.cost_estimate],
        [0.1, 0.32, 0.32, 0.26],
    ))
    f += [h2("8. 致工厂的问题")]
    f.append(P(cn.REVIEW_NOTE_CN + "（Machine-translated — to be reviewed by a native speaker）", "muted"))
    f.append(table(["编号", "中文", "English"], [[mixed(q.id), mixed(q.cn or "（暂无译文，请见英文）"), mixed(q.en)] for q in fp.questions], [0.06, 0.47, 0.47]))
    f += [h2("9. 假设清单"), P("见本文档末尾的“假设清单 / Assumption register”。", "small")]
    return f


# ---------------------------------------------------------------------------- stage renderers


def r_brief(a: Any) -> list[Any]:
    f = [kv([
        ("Product", mixed(a.product_name)), ("One-liner", mixed(a.one_liner)), ("Category", mixed(a.category)), ("Mode", mixed(a.mode)),
        ("Prompt", mixed(a.prompt)), ("Target markets", mixed(", ".join(a.target_markets))), ("Target retail price", lv_src(a.target_retail_price)),
        ("Target volumes", mixed(" / ".join(f"{v:,}" for v in a.target_volumes) + " units")),
        ("Battery / wireless", mixed(("battery" if a.has_battery else "no battery") + " · " + (", ".join(a.wireless) or "no radio"))),
    ])]
    f += [h2("Key features")] + bullets(a.key_features) + [h2("Constraints")] + (bullets(a.constraints) or [P("—")])
    if a.pasted_bom:
        f += [h2("Pasted BOM (prototype mode)"), table(["Part", "Qty", "Unit cost"], [[mixed(b.part), num(b.qty), lvs(b.unit_cost_est) if b.unit_cost_est else "—"] for b in a.pasted_bom], [0.6, 0.1, 0.3])]
    if a.clarifying_questions:
        f += [h2("Clarifying questions"), table(["Topic", "Question", "Answer"], [[mixed(q.topic), mixed(q.question), "skipped" if q.skipped or not q.answer else mixed(q.answer)] for q in a.clarifying_questions], [0.14, 0.56, 0.3])]
    return f


def r_design(a: Any) -> list[Any]:
    rows = [[("[chosen] " if d.id == a.chosen_direction_id else "") + mixed(d.name), mixed(d.description), mixed(d.shape), mixed(f"{d.material} — {d.finish}"), dims_str(d.dimensions)] for d in a.directions]
    f = [table(["Direction", "Description", "Shape", "Material / finish", "Dimensions"], rows, [0.12, 0.31, 0.15, 0.17, 0.25])]
    if a.chosen_direction_id:
        f.append(P(f"Chosen direction: {a.chosen_direction_id}", "small"))
    return f


def r_spec(a: Any) -> list[Any]:
    f = [kv([("Product", mixed(a.product_name)), ("Direction", mixed(a.direction_id)), ("Overall dimensions", dims_str(a.overall_dimensions)), ("Weight", lv_src(a.weight)), ("Tolerances", mixed("; ".join(a.tolerances)) or "—")])]
    f += [h2("Parts"), table(["Part", "Material", "Finish", "Process", "Tolerance", "Dimensions", "Wall"],
          [[mixed(p.name), mixed(p.material), mixed(p.finish), mixed(process_label(p.process_hint) if p.process_hint else "—"), mixed(p.tolerance or "—"), dims_str(p.dimensions) if p.dimensions else "—", lvs(p.wall_thickness) if p.wall_thickness else "—"] for p in a.parts],
          [0.14, 0.15, 0.13, 0.1, 0.16, 0.19, 0.13])]
    if a.electronics_blocks:
        f += [h2("Electronics block diagram"), table(["Block", "Function"], [[mixed(b.name), mixed(b.function)] for b in a.electronics_blocks], [0.3, 0.7])]
        names = {b.id: b.name for b in a.electronics_blocks}
        f += bullets([f"{names.get(e.source, e.source)} -> {names.get(e.target, e.target)}: {e.signal}" for e in a.electronics_edges], "small")
    f += [h2("Bill of materials"), table(["Part", "Cat.", "Qty", "Unit cost", "LCSC", "Risk"],
          [[mixed(b.part), mixed(b.category), num(b.qty), lvs(b.unit_cost_est) if b.unit_cost_est else "—", mixed(b.lcsc_pn or "—"), _risk_str(b)] for b in a.bom],
          [0.27, 0.09, 0.05, 0.18, 0.09, 0.32])]
    f += [h2("CAD files")] + (bullets([f"{c.format.upper()} — {c.url}" for c in a.cad_files], "small") or [P("—")])
    return f


def r_dfm(a: Any) -> list[Any]:
    f = [table(["#", "Severity", "Method", "Finding", "Fix", "Rule cited"],
          [[mixed(i.id), mixed(i.severity), "Measured" if i.method == "measured" else "AI-reviewed", mixed(i.description) + (f"<br/>{lvs(i.measurement)}" if i.measurement else ""), mixed(i.fix) + (f"<br/><i>Resolved: {mixed(i.resolution or 'yes')}</i>" if i.resolved else ""), mixed(i.rule_citation)] for i in a.issues],
          [0.04, 0.09, 0.09, 0.28, 0.28, 0.22])]
    if a.component_risks:
        f += [h2("Component risks"), table(["Part", "Level", "Reasons", "Alternatives", "Stock", "Lead time"],
              [[mixed(c.part), mixed(c.level), mixed("; ".join(c.reasons)), mixed("; ".join(c.alternatives) or "—"), lvs(c.stock) if c.stock else "—", lvs(c.lead_time_weeks) if c.lead_time_weeks else "—"] for c in a.component_risks],
              [0.19, 0.07, 0.24, 0.22, 0.14, 0.14])]
    if a.certifications:
        f += [h2("Certifications by market"), table(["Market", "Standard", "Why", "Cost", "Lead time"],
              [[mixed(c.market), mixed(c.standard), mixed(c.applies_because), lvs(c.cost_est), lvs(c.lead_time_weeks)] for c in a.certifications],
              [0.08, 0.3, 0.26, 0.19, 0.17])]
    return f


def r_costs(a: Any) -> list[Any]:
    f = [kv([("Target retail price", lv_src(a.target_retail_price)), ("Total cash needed", lv_src(a.total_cash_needed)), ("Tooling total", lv_src(a.tooling_total)),
             ("Certification total", lv_src(a.certification_total)), ("Break-even", lv_src(a.breakeven_units)), ("Volume factor", lv_src(a.volume_factor)), ("Reference quantity", mixed(f"{a.reference_quantity:,} units (input)"))])]
    f += [h2("Unit cost by volume tier"), table(["Qty", "BOM", "Assembly", "Packaging", "Unit cost", "Tooling / unit", "Margin"],
          [[num(t.quantity), lvs(t.bom_cost), lvs(t.assembly_cost), lvs(t.packaging_cost), lvs(t.unit_cost), lvs(t.tooling_amortisation), lvs(t.margin_pct)] for t in a.tiers],
          [0.07, 0.14, 0.14, 0.14, 0.17, 0.17, 0.17])]
    f += [h2("Cash needed (first order)"), table(["Component", "Amount"], [[mixed(c.name), lv_src(c.amount)] for c in a.cash_breakdown], [0.45, 0.55])]
    f += [h2("Tooling"), table(["Item", "Process", "Cost"], [[mixed(t.name), mixed(process_label(t.process)), lv_src(t.cost)] for t in a.tooling], [0.4, 0.15, 0.45])]
    f += [h2("BOM cost lines (LCSC-matched lines show price, stock and snapshot date)"), table(["Part", "Qty", "Unit price", "LCSC", "Stock", "Extended"],
          [[mixed(l.part), num(l.qty_per_unit), lv_src(l.unit_price), mixed(l.lcsc_pn or "—"), lvs(l.stock) if l.stock else "—", lvs(l.extended)] for l in a.bom_lines],
          [0.22, 0.05, 0.27, 0.09, 0.15, 0.22])]
    return f


def r_production(a: Any) -> list[Any]:
    f = [table(["Part", "Process", "Why", "Region", "Lead time"], [[mixed(s.part_name), mixed(process_label(s.process)), mixed(s.reason), mixed(s.region), lvs(s.lead_time_days)] for s in a.steps], [0.16, 0.13, 0.35, 0.15, 0.21])]
    f += [sp(4), kv([("Total lead time", lv_src(a.total_lead_time_days))])]
    if a.assembly_notes:
        f += [h2("Assembly notes")] + bullets(a.assembly_notes, "small")
    return f


def r_matching(a: Any) -> list[Any]:
    f = [P(f"Factory Pack: {a.factory_pack_id}", "small")]
    f += [table(["Process", "Material", "Quantity", "Certifications required", "Deadline"], [[mixed(process_label(q.process)), mixed(q.material), num(q.quantity), mixed(", ".join(q.certifications_required) or "—"), mixed(q.deadline or "—")] for q in a.queries], [0.2, 0.2, 0.12, 0.28, 0.2])]
    f += [h2("Shortlist")]
    for m in a.shortlist:
        rows = [[mixed(c.criterion), f"{c.score:.2f}", f"{c.weight:.2f}", mixed(c.note)] for c in m.score_breakdown]
        f.append(KeepTogether([P(f"#{m.rank} {m.factory_name}", "h2"), M(f"Score {lvs(m.score)}"), table(["Criterion", "Score 0-1", "Weight", "Note"], rows, [0.22, 0.12, 0.1, 0.56]), P("Reasons: " + "; ".join(m.reasons), "small")]))
    return f


def _quote_tiers(q: Any) -> str:
    return mixed("; ".join(f"{t.quantity:,} u: ${num(t.unit_price_usd)}" for t in q.tiers))


def r_negotiation(a: Any) -> list[Any]:
    f = [h2("Quotes (all values Fictional — demo data)"), table(["Quote", "Factory", "v", "Unit price by tier (USD)", "Tooling (USD)", "MOQ", "Lead time", "Terms / exceptions", "Status"],
          [[mixed(q.id), mixed(q.factory_id), str(q.version), _quote_tiers(q), num(q.tooling_usd), num(q.moq), f"{q.lead_time_days} d", mixed(q.payment_terms + ("; " + "; ".join(q.exceptions) if q.exceptions else "")), mixed(q.status)] for q in a.quotes],
          [0.14, 0.1, 0.03, 0.22, 0.08, 0.05, 0.06, 0.22, 0.10])]
    f += [h2("Recommendation"), P(f"{a.recommendation.factory_id} — quote {a.recommendation.quote_id}: {a.recommendation.rationale}")]
    if a.final_terms:
        t = a.final_terms
        f += [h2("Final terms" + (" (approved by the user)" if a.user_approved else " (awaiting approval)")), kv([("Factory / quote", mixed(f"{t.factory_id} / {t.quote_id}")), ("Quantity", mixed(f"{t.quantity:,} units")), ("Unit price", lv_src(t.unit_price)), ("Tooling", lv_src(t.tooling)), ("MOQ", mixed(f"{t.moq:,} units")), ("Lead time", lv_src(t.lead_time_days)), ("Payment terms", mixed(t.payment_terms))])]
    else:
        f += [P("Not approved yet: no final terms stored.", "small")]
    f += [h2("Negotiation transcript")]
    rows = []
    for t in a.transcript:
        msg = mixed(t.message) + (f"<br/>{mixed(t.message_cn)}" if t.message_cn else "") + (f"<br/><i>{mixed(t.rationale)}</i>" if t.rationale else "")
        rows.append([str(t.turn), mixed(t.speaker), mixed(t.factory_id), msg])
    f.append(table(["#", "Speaker", "Factory", "Message"], rows, [0.04, 0.13, 0.12, 0.71]))
    return f


def r_tooling(a: Any) -> list[Any]:
    f = [table(["Milestone", "Kind", "Start", "End", "Duration", "Payment", "Depends on"],
          [[mixed(m.name), mixed(m.kind), str(m.start_date), str(m.end_date), lvs(m.duration_days), lvs(m.payment) if m.payment else "—", mixed(", ".join(m.depends_on) or "—")] for m in a.milestones],
          [0.25, 0.12, 0.09, 0.09, 0.13, 0.19, 0.13])]
    f += [h2("Payment schedule"), table(["Milestone", "Description", "% of order", "Amount", "Due"], [[mixed(p.milestone_id), mixed(p.description), num(p.pct_of_order) if p.pct_of_order is not None else "—", lvs(p.amount), str(p.due_date)] for p in a.payment_schedule], [0.1, 0.35, 0.1, 0.27, 0.18])]
    return f


def r_qc(a: Any) -> list[Any]:
    f = [kv([("Standard", mixed(f"{a.standard}, level {a.inspection_level}")), ("Lot size", mixed(f"{a.lot_size:,} units (input)")), ("Sample size", lv_src(a.sample_size)), ("Inspection", lv_src(a.inspection_man_days)), ("Man-day rate", lv_src(a.man_day_rate)), ("Inspection cost", lv_src(a.inspection_cost))])]
    f += [h2("Defect classes (each mapped to a spec line)"), table(["#", "Severity", "Defect", "Spec reference", "Check", "AQL"], [[mixed(d.id), mixed(d.severity), mixed(d.description), mixed(d.spec_ref), mixed(d.check_method), num(d.aql)] for d in a.defects], [0.05, 0.09, 0.31, 0.2, 0.28, 0.07])]
    return f


def r_logistics(a: Any) -> list[Any]:
    f = [kv([("Incoterm", mixed(a.incoterm)), ("Destination", mixed(a.destination)), ("Quantity", mixed(f"{a.quantity:,} units")), ("Chosen mode", mixed(a.chosen_mode)), ("Section 122 surcharge applied", "yes" if a.section_122_applied else "no (toggle)"), ("Landed cost per unit", lv_src(a.landed_cost_per_unit)), ("Reconciles with stage 5", "yes" if a.reconciles_with_stage5 else "NO"), ("Reconciliation", mixed(a.reconciliation_note))])]
    f += [h2("Freight options (Fictional — demo data)"), table(["Mode", "Transit", "Cost per unit"], [[mixed(o.mode), lvs(o.transit_days), lvs(o.cost_per_unit)] for o in a.freight_options], [0.2, 0.4, 0.4])]
    f += [h2("HTS line"), kv([("Code", mixed(a.hts.code)), ("Description", mixed(a.hts.description)), ("General rate", lv_src(a.hts.general_rate)), ("Section 301 rate", lv_src(a.hts.section_301_rate)), ("Source", mixed(a.hts.source_url))])]
    f += [h2("Landed cost breakdown (per unit)"), table(["Component", "Amount"], [[mixed(c.name), lv_src(c.amount)] for c in a.landed_cost_breakdown], [0.4, 0.6])]
    return f


def r_financing(a: Any) -> list[Any]:
    rows = [("Total cash", lv_src(a.total_cash))]
    if a.matches_stage5_total:
        rows.append(("Stage 5 budget", "matches stage 5 total"))
    else:
        rows.append(("Stage 5 budget", (lv_src(a.stage5_total) + " — " if a.stage5_total else "") + mixed(a.reconciliation_note or "differs from stage 5")))
    f = [kv(rows)]
    f += [h2("Cash curve"), table(["Date", "Milestone", "Description", "Cash out", "Cumulative"], [[str(c.date), mixed(c.milestone_id), mixed(c.description), lvs(c.cash_out), lvs(c.cumulative)] for c in a.cash_curve], [0.12, 0.1, 0.34, 0.22, 0.22])]
    f += [h2("Financing options"), table(["Option", "Description", "Cost", "Pros", "Cons"], [[mixed(o.name), mixed(o.description), lvs(o.cost) if o.cost else "—", mixed("; ".join(o.pros)), mixed("; ".join(o.cons))] for o in a.options], [0.16, 0.3, 0.14, 0.2, 0.2])]
    return f


def r_brand(a: Any) -> list[Any]:
    f = [h2("Name options"), table(["Name", "Rationale"], [[mixed(n.name + (" [chosen]" if n.name == a.chosen_name else "")), mixed(n.rationale)] for n in a.name_options], [0.25, 0.75])]
    p = a.packaging
    f += [h2("Packaging"), kv([("Box", mixed(p.box_type)), ("Dimensions", dims_str(p.dimensions)), ("Materials", mixed(", ".join(p.materials))), ("Printing", mixed(p.printing)), ("Contents", mixed(", ".join(p.contents))), ("Unit cost", lv_src(p.unit_cost))])]
    lc = a.landing_copy
    f += [h2("Landing copy"), P(lc.headline, "h2"), P(lc.subheadline)] + bullets(lc.bullets) + [P("CTA: " + lc.cta, "small")]
    for lst in (a.shopify_listing, a.amazon_listing):
        f += [h2(f"{lst.channel.capitalize()} listing"), kv([("Title", mixed(lst.title)), ("Description", mixed(lst.description)), ("Bullets", mixed("; ".join(lst.bullets))), ("Price", lv_src(lst.price)), ("Keywords", mixed(", ".join(lst.keywords)))])]
    return f


RENDERERS: dict[int, Callable[[Any], list[Any]]] = {
    1: r_brief, 2: r_design, 3: r_spec, 4: r_dfm, 5: r_costs, 6: r_production, 7: r_matching, 8: r_negotiation,
    9: r_tooling, 10: r_qc, 11: r_logistics, 12: r_financing, 13: r_brand,
}
FICTIONAL_STAGES = {7, 8, 11}


def generic(obj: Any, depth: int = 0) -> list[Any]:
    """Last-resort dump of any artifact: labeled values keep their label."""
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    rows: list[tuple[str, str]] = []

    def is_lv(d: Any) -> bool:
        return isinstance(d, dict) and {"value", "unit", "label", "source_or_assumption"} <= set(d)

    def walk(path: str, v: Any) -> None:
        if is_lv(v):
            rows.append((path, f"{mixed(num(v['value']))} {mixed(v['unit'])} {chip(v['label'])}"))
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ("project_id", "generated_at"):
                    continue
                walk(f"{path}.{k}" if path else k, x)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(f"{path}[{i}]", x)
        elif v is not None:
            rows.append((path, mixed(str(v))))

    walk("", data)
    return [kv(rows[:400], (0.34, 0.66))] if rows else [P("—")]


def _stage_source(ctx: StageContext, n: int) -> tuple[Any, str]:
    """Returns (artifact, note kind): 'live' | 'cached' | 'missing' (cached example shown because the stage was not run)."""
    a = ctx.artifact(n)
    if a is not None:
        return a, "cached" if a.fallback else "live"
    from api.stages.runner import load_fixture

    return load_fixture(ctx.project.example, n, ctx.project.id), "missing"


def stage_section(ctx: StageContext, n: int) -> list[Any]:
    try:
        a, kind = _stage_source(ctx, n)
    except Exception as e:  # noqa: BLE001
        return [PageBreak(), h1(f"Stage {n} — {STAGE_TITLES[n]}", f"Stage {n} - {STAGE_TITLES[n]}", 1), P(f"Stage output unavailable ({type(e).__name__}).")]
    f: list[Any] = [PageBreak(), h1(f"Stage {n} — {STAGE_TITLES[n]}", f"Stage {n} - {STAGE_TITLES[n]}", 1)]
    f.append(P(f"status {a.status} · generated by {a.generated_by} · {a.generated_at:%Y-%m-%d %H:%M} UTC", "muted"))
    f.append(sp(7))
    if n in FICTIONAL_STAGES:
        f.append(M(mixed(FICTIONAL_BANNER), "banner_red"))
    if kind == "cached":
        f.append(M(mixed(f"Cached example — this stage fell back to a pre-built fixture ({a.fallback_reason or 'reason not recorded'}). It may describe a different product."), "banner_amber"))
    elif kind == "missing":
        f.append(M(mixed(f"Cached example — stage {n} was not run for this project; the pre-built {ctx.project.example or 'desk_lamp'} output is shown."), "banner_amber"))
    try:
        f += RENDERERS[n](a)
    except Exception as e:  # noqa: BLE001
        log.warning("stage %d renderer failed (%s) → generic dump", n, e)
        try:
            f += generic(a)
        except Exception as e2:  # noqa: BLE001
            f.append(P(f"Stage output could not be rendered ({type(e2).__name__})."))
    return f


# ---------------------------------------------------------------------------- register, legend, cover


def collect_assumptions(ctx: StageContext, fp: Any) -> list[Assumption]:
    seen: set[str] = set()
    out: list[Assumption] = []
    sources: list[tuple[int | None, list[Assumption]]] = [(n, ctx.artifacts[n].assumptions) for n in sorted(ctx.artifacts)]
    sources.append((None, list(fp.assumption_register)))
    for stage, items in sources:
        for a in items:
            key = a.text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(a if a.stage is not None or stage is None else a.model_copy(update={"stage": stage}))
    return out


def assumption_section(ctx: StageContext, fp: Any) -> list[Any]:
    items = collect_assumptions(ctx, fp)
    f: list[Any] = [PageBreak(), h1("Assumption register", "Assumption register", 0)]
    f.append(P("Every assumption behind a number in this dossier, with its label and source. Numbers labeled Estimate must be replaced by quotes or measurements before production.", "muted"))
    f.append(sp(4))
    f.append(table(["#", "Stage", "Assumption", "Label", "Source"],
                   [[mixed(a.id), str(a.stage) if a.stage is not None else "—", mixed(a.text), chip(a.label), mixed(a.source or "—")] for a in items],
                   [0.07, 0.06, 0.5, 0.13, 0.24]))
    return f


def legend_section() -> list[Any]:
    f: list[Any] = [PageBreak(), h1("Label legend", "Label legend", 0)]
    f.append(P("Four labels are used on screen and in this PDF. A number never appears without one of them.", "body"))
    f.append(sp(4))
    rows = [
        [chip("measured"), "Computed on the CAD (build123d / OCCT geometry checks: draft, undercuts, projection, wall thickness)."],
        [chip("sourced"), "A real price or official rate with its source and snapshot date (LCSC/JLCPCB via jlcsearch, USITC HTS, CBP notices, published benchmarks)."],
        [chip("estimate"), "An assumption shown to the reader; replace with a quote or measurement before committing money."],
        [chip("fictional"), "Simulated network: the factories, their capacity, quotes and negotiation replies, freight rates and past performance. Demo data, no real factory."],
    ]
    f.append(table(["Label", "Meaning"], rows, [0.25, 0.75]))
    f += [h2("Real vs simulated"),
          P("Real (live AI + code): brief, design, CAD/STEP/GLB, spec, measured DFM checks, certification map, real LCSC component prices, cost engine, production plan, brand kit, plans for tooling / QC / financing."),
          P("Simulated (labeled): the factories, their capacity, quotes and negotiation replies; freight rates; past performance."),
          h2("Human review"),
          P("AI drafts; an engineer must review every Factory Pack before it reaches a real factory. Chinese text is machine-translated and must be reviewed by a native speaker."),
          P("Pages marked \"Cached example\" show pre-built demo output instead of live output for this project.")]
    return f


def cached_stages(ctx: StageContext) -> list[int]:
    """Stages 1-7 that served a cached example (fallback) — they drive the wow screen and the Factory Pack."""
    return [n for n in range(1, 8) if (a := ctx.artifact(n)) is not None and a.fallback]


def cover_section(ctx: StageContext, fp: Any) -> list[Any]:
    f: list[Any] = [Spacer(1, 30 * mm), Heading(mixed("Launch Dossier"), ST["title"], outline="Cover", level=0)]
    f.append(P(ctx.project.name or fp.product_name, "subtitle"))
    f.append(P(f"Project {ctx.project.id} · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · PhysicalLovableX", "muted"))
    f.append(sp(8))
    if cached := cached_stages(ctx):
        f.append(M(mixed(f"{CACHED_NOTE} (stages {', '.join(map(str, cached))}). Numbers derived from those stages "
                         "describe the example product, not this project."), "banner_amber"))
        f.append(sp(6))
    rows: list[tuple[str, str]] = []
    costs, logi = ctx.artifact(5), ctx.artifact(11)
    if costs is not None:
        rows.append(("Target retail price", lvs(costs.target_retail_price)))
        for t in costs.tiers:
            rows.append((f"Unit cost @ {t.quantity:,} units (ex-works)", lvs(t.unit_cost)))
        rows.append(("Total cash needed", lvs(costs.total_cash_needed)))
        rows.append(("Break-even", lvs(costs.breakeven_units)))
    if logi is not None:
        rows.append(("Landed cost per unit", lvs(logi.landed_cost_per_unit)))
    if rows:
        f += [h2("Headline numbers"), kv(rows, (0.42, 0.58))]
    f += [h2("Contents and stage status")]
    srows = []
    for n in range(1, 14):
        a = ctx.artifact(n)
        state = "not run — cached example shown" if a is None else ("cached example (fallback)" if a.fallback else ("pre-built example" if a.generated_by == "fixture" else "live"))
        srows.append([str(n), mixed(STAGE_TITLES[n]), mixed(a.status if a else "not_started"), mixed(state)])
    f.append(table(["#", "Stage", "Status", "Source"], srows, [0.06, 0.4, 0.2, 0.34]))
    f.append(sp(6))
    f.append(M(mixed("Read with the label legend on the last page. Chinese text is machine-translated — to be reviewed by a native speaker. AI drafts; an engineer reviews before a real factory sees this."), "banner_blue"))
    return f


# ---------------------------------------------------------------------------- provider


def build_pdf(ctx: StageContext) -> bytes:
    fp = ctx.factory_pack
    if fp is None:
        from api.export.factory_pack import build_factory_pack

        fp = build_factory_pack(ctx)
    story: list[Any] = []
    story += cover_section(ctx, fp)
    story.append(PageBreak())
    story += factory_pack_en(fp)
    story += factory_pack_cn(fp)
    for n in range(1, 14):
        story += stage_section(ctx, n)
    story += assumption_section(ctx, fp)
    story += legend_section()
    buf = io.BytesIO()
    doc = Doc(
        buf,
        footer_text=(("CACHED EXAMPLE — AI unavailable · " if cached_stages(ctx) else "")
                     + f"PhysicalLovableX · Launch Dossier · {ctx.project.name} · Measured / Sourced / Estimate / Fictional — demo data"),
        title=f"Launch Dossier — {ctx.project.name}",
        author="PhysicalLovableX",
        subject="Factory Pack (EN + CN), 13 stage outputs, assumption register",
        keywords="factory pack, launch dossier",
    )
    doc.build(story, onFirstPage=doc.on_page, onLaterPages=doc.on_page)
    return buf.getvalue()


@provider("export_pdf")
def export_pdf(ctx: StageContext) -> bytes:
    """Never returns an empty document: a failure while composing falls back to a minimal, honest PDF."""
    try:
        data = build_pdf(ctx)
        if data[:4] == b"%PDF" and len(data) > 2000:
            return data
        raise ValueError("empty PDF")
    except Exception as e:  # noqa: BLE001
        log.warning("Launch Dossier composition failed (%s) → minimal PDF", e, exc_info=True)
        from api.stages.defaults import stub_pdf

        return stub_pdf(ctx)
