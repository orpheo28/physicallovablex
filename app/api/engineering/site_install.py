"""Site-install mode (category solar_roof): the pipeline speaks "installers" instead of "factories". Owner: W20.

    is_site_install(ctx) -> bool
    installer_queries(ctx, qty) -> [SearchCapacityQuery] | None   # stage 7 hook (api/agents/negotiation/_inputs.py)
    installers(limit=3) -> [InstallerMatch]

The three installers are Fictional — demo data records in factory_mcp/data/factories.json (ids `i_*`, process
`other` = site installation, which no factory in the network runs), so a solar query shortlists exactly them.
"""

from __future__ import annotations

from contracts.artifacts import InstallerMatch, ProcessType, SearchCapacityQuery

from api.engineering.category import detect_category

INSTALLER_PREFIX = "i_"
INSTALL_MATERIAL = "PV modules"
INSTALLER_CERTS = ["ISO 9001"]


def project_text(ctx) -> str:
    brief = ctx.artifact(1)
    parts = [ctx.project.prompt, ctx.project.name]
    if brief is not None:
        parts += [brief.product_name, brief.one_liner, " ".join(brief.key_features or [])]
    return " ".join(p for p in parts if p)


def is_site_install(ctx) -> bool:
    brief = ctx.artifact(1)
    return detect_category(project_text(ctx), getattr(brief, "category", None)) == "solar_roof"


def installer_queries(ctx, quantity: int = 1) -> list[SearchCapacityQuery] | None:
    """Stage 7 queries for a site-install project (None for a manufactured product: the normal factory queries apply)."""
    if not is_site_install(ctx):
        return None
    return [SearchCapacityQuery(process=ProcessType.other, material=INSTALL_MATERIAL, quantity=max(1, int(quantity)),
                                certifications_required=INSTALLER_CERTS)]


def installers(limit: int = 3) -> list[InstallerMatch]:
    from factory_mcp import network

    q = SearchCapacityQuery(process=ProcessType.other, material=INSTALL_MATERIAL, quantity=1, certifications_required=INSTALLER_CERTS)
    out = []
    for m in network.search_capacity(q, limit=limit):
        f = network.get_factory(m.factory_id)
        if f is None or not f.id.startswith(INSTALLER_PREFIX):
            continue
        out.append(InstallerMatch(factory_id=f.id, name=f.name, region=f.region, certifications=list(f.capacity.certifications),
                                  lead_time_days=f.capacity.lead_time_days))
    return out
