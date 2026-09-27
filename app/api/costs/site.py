"""Site-install costing (W21c): rooftop solar is priced per installation, not per unit at 500 / 2,000 / 10,000.

    is_site(ctx) -> bool
    site_costs(ctx) -> CostsArtifact        # stage 5: one tier = a pilot of PILOT installations, per-installation figures
    site_logistics(ctx, costs) -> LogisticsArtifact   # stage 11: kit bought from an EU distributor, no import by the installer

One currency per project: USD (the engineering layer converts its EUR/Wp and EUR/kWh at the same assumed FX).
unit_cost = installer cost of one installation (equipment from the BOM + installation labour + site admin);
target_retail_price = turnkey installed price (the engineering layer's EUR/Wp turnkey price, plus a battery when the BOM
has one, sold at the battery's equipment price × BATTERY_MARKUP); margin = (installed price − cost) / installed price.
"""

from __future__ import annotations

import re

from contracts.artifacts import (
    Assumption,
    CostLine,
    CostsArtifact,
    CostTier,
    FreightOption,
    HTSLine,
    LandedCostComponent,
    LogisticsArtifact,
)

from ._common import lv, usd

PILOT = 10  # installations in the pilot the cash plan covers
EUR_TO_USD = 1.08
LABOUR_EUR_PER_WP = 0.30  # two installers, residential pitched roof, EU 2026 range 0.25-0.40 EUR/Wp
SITE_ADMIN_EUR = 600.0  # scaffolding / safety line, permit file, grid-connection request, commissioning visit
BATTERY_MARKUP = 1.35
INSTALLER_FIXED_EUR = 2500.0  # installer qualification (e.g. RGE QualiPV) + ten-year liability insurance, first year
# W21d: fixed costs of running the pilot, spread over its installations (break-even is counted in installations)
PILOT_FIXED_EUR = {"Tools, van share and safety gear (pilot year)": 8000.0, "Sales and marketing for the pilot": 4000.0}


def is_site(ctx) -> bool:
    try:
        from api.engineering.site_install import is_site_install

        return is_site_install(ctx)
    except Exception:  # noqa: BLE001
        return False


def _solar(ctx):
    from api.engineering.site_install import project_text
    from api.engineering.solar import solar_design

    return solar_design(project_text(ctx))


def _lines(ctx):
    """(CostLine rows, equipment total, battery equipment total)."""
    from api.costs.family_prices import estimate
    from api.costs.modules import estimate as module_price

    spec = ctx.artifact(3)
    rows, total, battery = [], 0.0, 0.0
    for it in spec.bom if spec is not None else []:
        base, note = None, ""
        if it.unit_cost_est is not None and it.unit_cost_est.label != "sourced" and "Placeholder" not in it.unit_cost_est.source_or_assumption \
                and "No match" not in it.unit_cost_est.source_or_assumption:
            base, note = it.unit_cost_est.value, it.unit_cost_est.source_or_assumption
        hit = estimate("solar_array", it.part) or estimate("solar_array", f"{it.part} {it.description or ''}") or module_price(it.part)
        if base is None and hit is not None:
            base, note = hit
        if base is None:
            base, note = 5.0, "Placeholder USD 5 per piece for a balance-of-system item without a price (Estimate)"
        ext = base * it.qty
        total += ext
        if re.search(r"batter|storage|kwh", it.part, re.I):
            battery += ext
        rows.append(CostLine(bom_item_id=it.id, part=it.part, qty_per_unit=it.qty, unit_price=usd(base, "estimate", note, nd=2),
                             extended=usd(ext, "estimate", f"{it.qty:g} × {base:,.2f} per installation", nd=2)))
    return rows, total, battery


def installed_price(ctx, sol=None, battery: float | None = None):
    """THE customer price of one installation (W21e: one source of truth): PV turnkey + battery system when the BOM has
    one. → (LabeledValue USD, PV turnkey, battery retail)."""
    sol = sol or _solar(ctx)
    if battery is None:
        battery = _lines(ctx)[2]
    turnkey = sol.install_cost.value
    extra = battery * BATTERY_MARKUP
    note = (f"Installed price of one installation ({sol.peak_power.value:.2f} kWp{' + battery' if battery else ''}): PV turnkey ${turnkey:,.0f}"
            + (f" + battery system ${extra:,.0f} (equipment × {BATTERY_MARKUP})" if battery else ""))
    return usd(turnkey + extra, "estimate", note, nd=2), turnkey, extra


def site_costs(ctx) -> CostsArtifact:
    sol = _solar(ctx)
    kwp = sol.peak_power.value
    rows, equipment, battery = _lines(ctx)
    labour = kwp * 1000 * LABOUR_EUR_PER_WP * EUR_TO_USD
    admin = SITE_ADMIN_EUR * EUR_TO_USD
    unit = equipment + labour + admin
    price, turnkey, _ = installed_price(ctx, sol, battery)
    installed = price.value
    margin = (installed - unit) / installed * 100 if installed else 0.0
    fixed = (INSTALLER_FIXED_EUR + sum(PILOT_FIXED_EUR.values())) * EUR_TO_USD  # pilot fixed-cost base
    contribution = installed - unit
    per = f"per installation ({kwp:.2f} kWp{' + battery' if battery else ''})"
    tier = CostTier(
        quantity=PILOT,
        bom_cost=usd(equipment, "estimate", f"Equipment from the BOM {per}: modules, inverter, mounting, cabling" + (", battery" if battery else "")),
        assembly_cost=usd(labour + admin, "estimate", f"Installation labour {kwp:.2f} kWp × {LABOUR_EUR_PER_WP} EUR/Wp + site admin {SITE_ADMIN_EUR:g} EUR (scaffolding, permit, grid request, commissioning) × {EUR_TO_USD} USD/EUR"),
        packaging_cost=usd(0, "estimate", "Not applicable: equipment delivered to the site by the distributor"),
        unit_cost=usd(unit, "estimate", f"Installer cost {per} = equipment + labour + site admin (what the installer pays — not the customer price)"),
        tooling_amortisation=usd(0, "estimate", "No tooling: bought-in certified equipment"),
        margin_pct=lv(margin, "pct", "estimate", f"(installed price ${installed:,.0f} − installer cost ${unit:,.0f}) ÷ installed price", nd=1),
    )
    first = unit * PILOT
    cash = [
        LandedCostComponent(name=f"Equipment for {PILOT} installations", amount=usd(equipment * PILOT, "estimate", f"{PILOT} × ${equipment:,.0f}")),
        LandedCostComponent(name=f"Installation labour + site admin ({PILOT} sites)", amount=usd((labour + admin) * PILOT, "estimate", f"{PILOT} × ${labour + admin:,.0f}")),
        LandedCostComponent(name="Installer qualification + liability insurance (first year)", amount=usd(INSTALLER_FIXED_EUR * EUR_TO_USD, "estimate", f"{INSTALLER_FIXED_EUR:g} EUR × {EUR_TO_USD} (e.g. RGE QualiPV + ten-year insurance, typical)")),
    ] + [LandedCostComponent(name=k, amount=usd(v * EUR_TO_USD, "estimate", f"{v:g} EUR × {EUR_TO_USD} (typical, pilot fixed cost)")) for k, v in PILOT_FIXED_EUR.items()]
    total = round(sum(c.amount.value for c in cash), 2)
    breakeven = int(-(-fixed // contribution)) if contribution > 0 else 0
    return CostsArtifact(
        project_id=ctx.project.id, generated_by="code", unit_basis="per_installation", currency="USD",
        assumptions=[
            Assumption(id="a1", text=f"Site install: priced per installation (one {kwp:.2f} kWp roof), cash plan for a pilot of {PILOT} installations — no factory volume tiers", label="estimate", stage=5),
            Assumption(id="a2", text=f"One currency per project (USD): EUR figures × {EUR_TO_USD} USD/EUR (assumed FX)", label="estimate", stage=5),
            Assumption(id="a3", text=f"Installed price = PV turnkey {sol.install_cost.source_or_assumption}" + (f" + battery at equipment price × {BATTERY_MARKUP}" if battery else ""), label="estimate", stage=5),
            Assumption(id="a4", text="Equipment prices are category trade estimates (not quotes): modules, inverter, mounting, cabling, battery", label="estimate", stage=5),
        ],
        bom_lines=rows,
        volume_factor=lv(1.0, "ratio", "estimate", "No volume curve for a site install", nd=3),
        tiers=[tier], tooling=[], tooling_total=usd(0, "estimate", "No tooling", nd=0),
        certification_total=usd(INSTALLER_FIXED_EUR * EUR_TO_USD, "estimate", "Installer qualification + ten-year liability insurance (typical, first year)", nd=0),
        reference_quantity=PILOT,
        total_cash_needed=usd(total, "estimate", f"Sum of cash_breakdown for a pilot of {PILOT} installations"),
        cash_breakdown=cash,
        target_retail_price=price,
        breakeven_units=lv(breakeven, "installations", "estimate", (
            f"Installations to recover the pilot's fixed costs ${fixed:,.0f} (qualification + insurance, tools / van share, sales) at "
            f"${contribution:,.0f} contribution each (${installed:,.0f} installed − ${unit:,.0f} installer cost), out of a pilot of {PILOT}"
            if contribution > 0 else "NOT REACHABLE: installer cost above the installed price"), nd=0),
    )


def site_logistics(ctx, costs) -> LogisticsArtifact:
    unit = costs.tiers[0].unit_cost.value
    zero = lambda why: usd(0, "estimate", why, nd=2)  # noqa: E731
    comps = [
        LandedCostComponent(name="Equipment (delivered to the installer's depot)", amount=costs.tiers[0].bom_cost),
        LandedCostComponent(name="Installation labour + site admin", amount=costs.tiers[0].assembly_cost),
        LandedCostComponent(name="Import duties", amount=zero("None paid by the installer: equipment bought from an EU distributor (PV modules CN 8541 43: 0% EU conventional duty, to be confirmed)")),
    ]
    return LogisticsArtifact(
        project_id=ctx.project.id, generated_by="code", incoterm="DDP",
        destination="Installer depot → customer roof (local delivery, EU)", quantity=costs.reference_quantity,
        freight_options=[FreightOption(mode="sea_fcl", transit_days=lv(0, "days", "estimate", "Stock at the EU distributor: no ocean leg for the installer", nd=0),
                                       cost_per_unit=zero("Delivery included in the distributor's equipment price"))],
        chosen_mode="sea_fcl",
        hts=HTSLine(code="8541.43", description="Photovoltaic modules — bought in the EU, no import by the installer",
                    general_rate=lv(0, "pct", "estimate", "EU conventional duty on PV modules 0% (to be confirmed); not paid by the installer", nd=1),
                    section_301_rate=lv(0, "pct", "estimate", "Not applicable: EU site, no US import", nd=1),
                    source_url="https://ec.europa.eu/taxation_customs/dds2/taric/"),
        landed_cost_breakdown=comps, landed_cost_per_unit=usd(unit, "estimate", "Installer cost per installation (stage 5)"),
        reconciles_with_stage5=True, reconciliation_note="Site install: landed cost = stage 5 installer cost per installation (no import, no freight leg).",
        assumptions=[Assumption(id="a1", text="Site install: the kit is bought from an EU distributor and delivered to the site; no customs or ocean freight for the installer", label="estimate", stage=11)],
    )


__all__ = ["is_site", "site_costs", "site_logistics", "PILOT"]
