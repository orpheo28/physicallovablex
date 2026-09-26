"""W0 default implementations used until (or when) a Wave 1 provider fails. Owner: W0."""

from __future__ import annotations

import io
import json

from contracts.artifacts import STAGE_TITLES, Factory, RFQWithQuotes

from api.stages.registry import StageContext
from api.stages.runner import FIXTURES_DIR

NETWORK_DIR = FIXTURES_DIR / "network"

EXAMPLE_KEYWORDS = {
    "desk_lamp": ("desk lamp", "lamp", "lampe"),
    "tracker_card": ("tracker card", "tracker", "wallet"),
}


def guess_example(prompt: str) -> str | None:
    """Map a prompt to a cached example (used for fallbacks). None → runner uses DEFAULT_EXAMPLE."""
    p = prompt.lower()
    for ex, words in EXAMPLE_KEYWORDS.items():
        if any(w in p for w in words) and (FIXTURES_DIR / ex / "project.json").exists():
            return ex
    return None


class FixtureNetwork:
    """Read-only simulated network from api/fixtures/network/*.json (W5's MCP provider supersedes it)."""

    def list_factories(self) -> list[Factory]:
        return [Factory.model_validate(f) for f in json.loads((NETWORK_DIR / "factories.json").read_text())]

    def get_factory(self, factory_id: str) -> Factory | None:
        return next((f for f in self.list_factories() if f.id == factory_id), None)

    def list_rfqs(self, factory_id: str) -> list[RFQWithQuotes]:
        items = [RFQWithQuotes.model_validate(r) for r in json.loads((NETWORK_DIR / "rfqs.json").read_text())]
        return [r for r in items if r.rfq.factory_id == factory_id]


def stub_pdf(ctx: StageContext) -> bytes:
    """Minimal Launch Dossier until W6's export_pdf provider is registered."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Launch Dossier (stub) — {ctx.project.name}")
    c.setFont("Helvetica", 10)
    y -= 30
    for n in range(1, 14):
        a = ctx.artifacts.get(n)
        state = "missing" if a is None else f"{a.status}{' · fallback' if a.fallback else ''}"
        c.drawString(50, y, f"{n:>2}. {STAGE_TITLES[n]}: {state}")
        y -= 16
    if ctx.factory_pack is not None:
        y -= 10
        c.drawString(50, y, f"Factory Pack {ctx.factory_pack.id} v{ctx.factory_pack.version}: {ctx.factory_pack.product_summary[:90]}")
    c.showPage()
    c.save()
    return buf.getvalue()
