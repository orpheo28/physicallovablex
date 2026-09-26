"""Offline tests for the costs package (no API key, temp DB). Run: uv run pytest api/costs"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("DB_PATH", str(Path(tempfile.mkdtemp()) / "costs_test.db"))
os.environ["OPENROUTER_API_KEY"] = ""

import pytest  # noqa: E402

from api import db  # noqa: E402
from api.costs import engine, financing, landed  # noqa: E402
from api.costs.lcsc import component_risk, match_bom  # noqa: E402
from api.stages import runner  # noqa: E402
from contracts.artifacts import BOMCategory, BOMItem, Project  # noqa: E402

runner.STAGE_HANDLERS.setdefault(5, engine.run_costs)
runner.STAGE_HANDLERS.setdefault(11, landed.run_logistics)
runner.STAGE_HANDLERS.setdefault(12, financing.run_financing)


@pytest.fixture(autouse=True, scope="module")
def _db():
    assert "app.db" not in str(db.DB_PATH)
    db.init_db()


def _project(pid: str, prompt: str, example: str | None) -> str:
    runner.save_project(Project(id=pid, name=pid, mode="idea", prompt=prompt, example=example))
    return pid


def _bom(*rows):
    return [BOMItem(id=f"e{i}", part=p, category=BOMCategory.electronic, qty=q) for i, (p, q) in enumerate(rows)]


# ----------------------------------------------------------------------- matcher


def test_match_usbc_and_lipo_charger_are_real_lcsc_parts():
    out = match_bom(_bom(("USB-C receptacle", 1), ("LiPo charger IC", 1)))
    for it in out:
        assert it.lcsc_pn and it.lcsc_pn.startswith("C") and it.lcsc_pn[1:].isdigit()
        assert it.unit_cost_est.label == "sourced"
        assert it.unit_cost_est.source_or_assumption == f"LCSC price, snapshot 2026-09-26, https://www.lcsc.com/product-detail/{it.lcsc_pn}.html"
        assert it.unit_cost_est.value > 0
    assert "USB" in out[0].description or "TYPE-C" in out[0].description.upper()


def test_unmatched_and_qty_break():
    out = match_bom(_bom(("Li-ion cell 18650 3000 mAh", 1), ("White LED 2835 4000K", 24)))
    assert out[0].lcsc_pn is None and out[0].unit_cost_est.label == "estimate" and "snapshot" in out[0].unit_cost_est.source_or_assumption
    small = match_bom(_bom(("White LED 2835 4000K", 1)), order_qty=1)[0].unit_cost_est.value
    big = match_bom(_bom(("White LED 2835 4000K", 1)), order_qty=100000)[0].unit_cost_est.value
    assert big <= small


def test_component_risk():
    items = match_bom(_bom(("USB-C receptacle", 1), ("Li-ion cell 18650 3000 mAh", 1), ("Mystery ASIC XQ9000", 1)))
    risks = {r.bom_item_id: r for r in component_risk(items)}
    assert risks["e0"].stock is not None and risks["e0"].stock.label == "sourced"
    assert any("UN38.3" in x for x in risks["e1"].reasons)
    assert risks["e2"].level != "low"


# ----------------------------------------------------------------------- stage 5


def test_stage5_live_not_fallback():
    pid = _project("t5", "Magnetic rechargeable desk lamp sold at 89 EUR", "desk_lamp")
    a = runner.run_stage(pid, 5)
    assert a.fallback is False and a.generated_by == "code"
    assert [t.quantity for t in a.tiers] == [500, 2000, 10000]
    units = [t.unit_cost.value for t in a.tiers]
    assert units[0] > units[1] > units[2]
    assert round(sum(c.amount.value for c in a.cash_breakdown), 2) == a.total_cash_needed.value
    assert a.tooling_total.value == pytest.approx(sum(t.cost.value for t in a.tooling))
    assert a.breakeven_units.value > 0 and a.target_retail_price.value > 0
    assert any(l.lcsc_pn for l in a.bom_lines)
    for l in a.bom_lines:
        if l.unit_price.label == "sourced":
            assert l.unit_price.source_or_assumption.startswith("LCSC price, ")
        else:
            assert l.unit_price.source_or_assumption


def test_stage5_inputs_and_bad_factor():
    pid = _project("t5b", "desk lamp", "desk_lamp")
    a = runner.run_stage(pid, 5, {"volumes": [1000, 5000, 20000], "volume_factor": 0.8, "reference_quantity": 5000})
    assert [t.quantity for t in a.tiers] == [1000, 5000, 20000] and a.reference_quantity == 5000 and a.volume_factor.value == 0.8
    bad = runner.run_stage(pid, 5, {"volume_factor": 1.7})
    assert bad.fallback is True


def test_stage5_other_product_template():
    pid = _project("t5c", "Bluetooth tracker card for wallets", "tracker_card")
    a = runner.run_stage(pid, 5)
    assert a.fallback is False
    assert round(sum(c.amount.value for c in a.cash_breakdown), 2) == a.total_cash_needed.value


def test_stage5_uses_spec_and_dfm_from_fixtures():
    pid = _project("t5d", "desk lamp", "desk_lamp")
    for n in (1, 3, 4):
        runner.save_artifact(pid, n, runner.load_fixture("desk_lamp", n, pid))
    a = runner.run_stage(pid, 5)
    assert a.fallback is False
    dfm = runner.get_artifact(pid, 4)
    req = sum(c.cost_est.value for c in dfm.certifications if c.required)
    assert a.certification_total.value == pytest.approx(req)
    assert any(t.process == "injection_molding" for t in a.tooling)


# ----------------------------------------------------------------------- landed / stage 11


def test_landed_components():
    hts = landed.hts_line("desk_lamp")
    comps, total = landed.landed_cost(12.0, 2000, "sea_lcl", hts, False, weight_kg=0.7, tooling_total=6000)
    names = {c.name: c.amount for c in comps}
    assert total.value >= 12.0 and total.value == pytest.approx(sum(c.amount.value for c in comps), abs=0.02)
    assert any(n.startswith("IEEPA") and v.value == 0 for n, v in names.items())
    assert any(n.startswith("Tooling") and v.value == pytest.approx(3.0) for n, v in names.items())
    on = landed.landed_cost(12.0, 2000, "sea_lcl", hts, True, weight_kg=0.7, tooling_total=6000)[1].value
    assert on == pytest.approx(total.value + 1.2, abs=0.02)
    assert landed.landed_cost(12.0, 2000, "air", hts, weight_kg=0.7)[1].value > landed.landed_cost(12.0, 2000, "sea_lcl", hts, weight_kg=0.7)[1].value


def test_hts_lines_cited():
    h = landed.hts_line("desk_lamp")
    assert h.code.startswith("8513.10.40") and h.general_rate.value == 3.5 and h.general_rate.label == "sourced"
    assert "2026-09-26" in h.general_rate.source_or_assumption and h.source_url.startswith("https://hts.usitc.gov")
    assert h.section_301_rate.label == "estimate" and "broker" in h.section_301_rate.source_or_assumption
    t = landed.hts_line("tracker_card")
    assert t.code.startswith("8517.62")


def test_stage11_and_12_reconcile():
    pid = _project("t11", "desk lamp", "desk_lamp")
    c = runner.run_stage(pid, 5)
    lg = runner.run_stage(pid, 11)
    assert lg.fallback is False
    assert lg.landed_cost_per_unit.value >= lg.landed_cost_breakdown[0].amount.value
    assert lg.reconciles_with_stage5 and lg.reconciliation_note
    assert {o.mode for o in lg.freight_options} == {"sea_lcl", "sea_fcl", "air", "express"}
    on = runner.run_stage(pid, 11, {"section_122": True})
    assert on.section_122_applied and on.landed_cost_per_unit.value > lg.landed_cost_per_unit.value
    fin = runner.run_stage(pid, 12)
    assert fin.fallback is False and fin.matches_stage5_total
    assert fin.total_cash.value == c.total_cash_needed.value
    assert {o.kind for o in fin.options} >= {"preorders", "crowdfunding", "inventory_financing"}
    assert financing.check_cash(fin.cash_curve, c) == []


def test_stage11_12_with_stage8_and_9_fixtures():
    pid = _project("t1112", "desk lamp", "desk_lamp")
    for n in (1, 3, 4, 8, 9):
        runner.save_artifact(pid, n, runner.load_fixture("desk_lamp", n, pid))
    c = runner.run_stage(pid, 5)
    lg = runner.run_stage(pid, 11)
    assert lg.fallback is False and lg.landed_cost_per_unit.value >= 13.0
    fin = runner.run_stage(pid, 12)
    # W7g B4: the approved quote (stage 8 fixture) replaces the estimate; stage 5 stays the budget reference
    ft = runner.get_artifact(pid, 8).final_terms
    assert fin.fallback is False and fin.stage5_total.value == c.total_cash_needed.value
    assert not fin.matches_stage5_total and fin.reconciliation_note.startswith("Differs from stage 5 by $")
    assert ft.quote_id in fin.reconciliation_note
    first = [p for p in fin.cash_curve if p.description.startswith("First production order")]
    assert abs(sum(p.cash_out.value for p in first) - ft.unit_price.value * ft.quantity) < 0.05
    tool = [p for p in fin.cash_curve if p.description.startswith("Tooling")]
    assert abs(sum(p.cash_out.value for p in tool) - ft.tooling.value) < 0.05
    assert abs(sum(p.cash_out.value for p in fin.cash_curve) - fin.total_cash.value) < 0.05
    ms = runner.get_artifact(pid, 9).milestones
    assert {p.milestone_id for p in fin.cash_curve} <= {m.id for m in ms}


def test_check_cash_detects_problems():
    pid = _project("tcc", "desk lamp", "desk_lamp")
    c = runner.run_stage(pid, 5)
    curve = financing.cash_curve(financing.standard_milestones(Project.model_validate(runner.get_project(pid)).created_at.date()), c)
    assert financing.check_cash(curve, c) == []
    curve[0] = curve[0].model_copy(update={"cash_out": curve[0].cash_out.model_copy(update={"value": curve[0].cash_out.value + 500})})
    assert financing.check_cash(curve, c)


def test_lcsc_matcher_does_not_substitute_other_families_or_classes():
    """W7: an ESP32 line must not match another vendor's MCU; a resistor line is not a USB connector; load cell ≠ battery."""
    from api.costs.lcsc import best_match

    assert best_match("ESP32-C3-WROOM-02-N4 Wi-Fi module") is None or "esp32" in best_match("ESP32-C3-WROOM-02-N4 Wi-Fi module").mfr.lower()
    r = best_match("USB-C CC pull-down resistors, 5.1 kΩ")
    assert r is None or r.category == "Resistors"
    items = [BOMItem(id="e1", part="Single-point strain-gauge load cell, 5 kg", category=BOMCategory.electronic, qty=1)]
    risks = component_risk(match_bom(items))
    assert not any("Li-ion" in x for r in risks for x in r.reasons)


def test_stage11_reuses_stage5_estimated_hts():
    from types import SimpleNamespace

    from contracts.artifacts import Assumption

    costs = SimpleNamespace(assumptions=[Assumption(id="a6", label="estimate", stage=5, text="Landed-cost basis: HTS 8423.10.0000 (general 0%, Section 301 25%), IEEPA 0")])
    h = landed._hts_from_stage5(costs)
    assert h.code == "8423.10.0000" and h.general_rate.value == 0 and h.general_rate.label == "estimate"


def test_keyboard_lines_and_cnc_parts_are_priced_sanely():
    """W7 (prompt 4 fallback): diodes are diodes, 104× small parts get a per-piece placeholder, CNC parts are costed."""
    from api.costs.lcsc import best_match
    from contracts.artifacts import SpecPart

    d = best_match("Switch-matrix diodes, SMD", part="Switch-matrix diodes, SMD")
    assert d is not None and d.category == "Diodes" and d.price(2000) < 0.05
    sockets = match_bom([BOMItem(id="e2", part="Hot-swap switch sockets, MX-compatible", description="soldered to the PCB", category=BOMCategory.electronic, qty=104)])
    assert sockets[0].unit_cost_est.value < 0.2
    cnc = SpecPart(id="p1", name="Top shell", material="Aluminium 6063-T5", finish="Anodised", process_hint="cnc",
                   dimensions={k: {"value": v, "unit": "mm", "label": "measured", "source_or_assumption": "bbox"} for k, v in (("length", 400), ("width", 135), ("height", 11))})
    cost, note = engine.part_cost(cnc)
    assert 5 < cost < 60 and "CNC" in note


def test_honesty_audit_items():
    """W7e (docs/HONESTY_AUDIT.md): LCSC URL on Sourced prices/stock, V-Trust cited + Sourced, IEEPA URL."""
    it = match_bom([BOMItem(id="e1", part="USB-C receptacle 16P SMD", category=BOMCategory.electronic, qty=2)])[0]
    assert f"https://www.lcsc.com/product-detail/{it.lcsc_pn}.html" in it.unit_cost_est.source_or_assumption
    risk = component_risk([it])[0]
    assert risk.stock is None or "lcsc.com/product-detail" in risk.stock.source_or_assumption
    comps, _ = landed.landed_cost(5.0, 2000, "sea_lcl", landed.hts_line("desk_lamp"))
    by = {c.name.split(" (")[0]: c.amount for c in comps}
    assert "content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9" in by["IEEPA surcharges"].source_or_assumption
    qc = by["Pre-shipment inspection"]
    assert qc.label == "estimate" and "V-Trust rate (Sourced) × estimated man-days" in qc.source_or_assumption
    assert "https://www.v-trust.com/en/our-network, checked 2026-09-26" in qc.source_or_assumption
