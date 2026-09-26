"""Offline tests for the Sourced-data layer: USITC HTS cache, CBP CROSS precedents, Drewry WCI. Reads committed caches only."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("DB_PATH", str(Path(tempfile.mkdtemp()) / "sourced_test.db"))
os.environ["OPENROUTER_API_KEY"] = ""

import pytest  # noqa: E402

from api import db  # noqa: E402
from api.costs import engine, financing, freight, landed  # noqa: E402
from api.costs import hts as hts_cache  # noqa: E402
from api.costs import precedent as cross  # noqa: E402
from api.stages import runner  # noqa: E402
from contracts.artifacts import Project  # noqa: E402

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


def test_duty_for_reads_cache():
    d = hts_cache.duty_for("8513.10.4000", "9903.88.03")
    assert d["code"] == "8513.10.40.00" and d["mfn_pct"] == 3.5 and d["s301_rate"] == 25.0 and d["fetched_on"]
    d = hts_cache.duty_for("8517.62.0090", "9903.88.15")
    assert d["mfn_pct"] == 0.0 and d["s301_rate"] == 7.5
    assert hts_cache.duty_for("0101.21.0000") is None  # heading not cached -> caller keeps its Estimate


def test_every_product_has_a_cache_and_no_precedent_is_invented():
    for slug in cross.PRODUCTS:
        assert (cross.CROSS_DIR / f"{slug}.json").exists()
        p = cross.find_precedent(slug, "")
        if p is not None:
            assert p.url == f"https://rulings.cbp.gov/ruling/{p.ruling}" and p.ruling_date
            assert landed.hts_from_precedent(p) is not None


def test_examples_resolve_to_sourced_precedents():
    lamp, p = landed.resolve_hts(None, "desk_lamp", "")
    assert p.ruling == "N248128" and lamp.code == "8513.10.40.00" and lamp.general_rate.label == "sourced"
    assert lamp.section_301_rate.label == "sourced" and "N350173" in lamp.section_301_rate.source_or_assumption
    trk, p = landed.resolve_hts(None, "tracker_card", "")
    assert p.ruling == "N305756" and trk.code == "8517.62.00.90" and trk.general_rate.value == 0
    assert trk.section_301_rate.value == 7.5 and trk.section_301_rate.label == "sourced"


def test_no_precedent_keeps_estimate():
    assert cross.find_precedent(None, "E-ink phone, minimalist") is None
    h, p = landed.resolve_hts(None, None, "Kids' audio player with NFC figurines")
    assert p is None and h.general_rate.label == "estimate"


def test_wci_lane_and_units():
    assert freight.lane_rate("Shanghai-Los Angeles")[0] == 7838 and freight.lane_rate("Shanghai-New York")[0] == 10373
    assert freight.lane_rate("Shanghai-Rotterdam") is None
    assert freight.units_per_feu(0.01) == 6700


def test_lcl_derived_from_lane_rate_with_minimum_and_premium():
    lane = "Shanghai-Los Angeles"
    per, chg, per_m3 = freight.lcl_per_unit(lane, 0.01, 2000)  # 20 m³
    assert per_m3 == pytest.approx(7838 / 67 * 1.5) and chg == pytest.approx(20) and per == pytest.approx(per_m3 * 20 / 2000)
    per, chg, _ = freight.lcl_per_unit(lane, 0.0005, 100)  # 0.05 m³ -> minimum 1 m³
    assert chg == 1.0 and per == pytest.approx(7838 / 67 * 1.5 / 100)
    _, label, note = landed.freight_detail("sea_lcl", 0.5, 0.01, lane, 2000)
    assert label == "estimate" and "derived from Drewry WCI 24 Sep 2026" in note
    assert landed.freight_detail("air", 0.5, None, lane, 2000)[1] == "fictional"  # no packed volume -> demo rate


def test_fcl_20ft_vs_40ft_and_cheaper_mode():
    lane = "Shanghai-Los Angeles"
    per, kind, n = freight.fcl_per_unit(lane, 0.01, 2000)  # 20 m³ -> one 20ft at 0.55 × 7838
    assert kind == "20ft" and n == 1 and per == pytest.approx(7838 * 0.55 / 2000)
    per, kind, n = freight.fcl_per_unit(lane, 0.01, 6000)  # 60 m³ -> one 40ft beats two 20ft (1.1×)
    assert kind == "40ft" and n == 1 and per == pytest.approx(7838 / 6000)
    assert freight.cheaper_sea_mode(lane, 0.01, 2000) == "sea_lcl"  # 3,861 LCL vs 4,311 20ft
    assert freight.cheaper_sea_mode(lane, 0.01, 6000) == "sea_fcl"  # 60 m³ LCL = 10,5k vs 7,838
    assert landed.choose_mode(6000, volume_m3=0.01, lane=lane) == "sea_fcl" and landed.choose_mode(6000, "air") == "air"
    fr = lambda mode, qty: next(c.amount for c in landed.landed_cost(10.0, qty, mode, None, volume_m3=0.01, lane=lane)[0] if c.name.startswith("Freight"))  # noqa: E731
    assert fr("sea_fcl", 6000).value == pytest.approx(7838 / 6000, abs=0.01) and "Drewry" in fr("sea_fcl", 6000).source_or_assumption
    assert fr("sea_lcl", 2000).label == "estimate"


@pytest.mark.parametrize("pid,prompt,example,ruling", [("s11t", "Bluetooth tracker card for wallets", "tracker_card", "N305756"), ("s11b", "Bike light with brake detection", None, "N257698")])
def test_stage11_sourced_and_reconciles(pid, prompt, example, ruling):
    _project(pid, prompt, example)
    c = runner.run_stage(pid, 5)
    lg = runner.run_stage(pid, 11)
    assert lg.fallback is False and lg.reconciles_with_stage5
    a = {x.id: x for x in lg.assumptions}
    assert ruling in a["a7"].text and a["a7"].label == "sourced" and f"https://rulings.cbp.gov/ruling/{ruling}" in a["a7"].text
    assert "Not a binding classification" in a["a7"].text
    assert a["a8"].label == "sourced" and "Drewry World Container Index, 24 Sep 2026" in a["a8"].text and "7,838" in a["a8"].text
    fcl = next(o for o in lg.freight_options if o.mode == "sea_fcl")
    assert "Drewry" in fcl.cost_per_unit.source_or_assumption and fcl.cost_per_unit.label == "estimate"
    lcl = next(o for o in lg.freight_options if o.mode == "sea_lcl")
    assert lcl.cost_per_unit.label == "estimate" and "derived from Drewry WCI 24 Sep 2026" in lcl.cost_per_unit.source_or_assumption
    assert "typical 1.3–2.0×" in a["a10"].text and a["a10"].label == "estimate"
    air = next(o for o in lg.freight_options if o.mode == "air").cost_per_unit
    exp = next(o for o in lg.freight_options if o.mode == "express").cost_per_unit
    assert air.label == exp.label == "estimate" and "to be confirmed by a forwarder" in air.source_or_assumption
    assert exp.value == pytest.approx(1.8 * air.value, abs=0.002) and lg.chosen_mode in ("sea_lcl", "sea_fcl")
    assert air.value > next(o for o in lg.freight_options if o.mode == "sea_lcl").cost_per_unit.value
    assert abs(sum(x.amount.value for x in lg.landed_cost_breakdown) - lg.landed_cost_per_unit.value) < 0.02
    fin = runner.run_stage(pid, 12)
    assert fin.total_cash.value == c.total_cash_needed.value


def test_east_coast_lane():
    pid = _project("s11ny", "Desk lamp shipped to the East Coast", "desk_lamp")
    runner.run_stage(pid, 5)
    lg = runner.run_stage(pid, 11)
    assert lg.destination.startswith("New York") and "10,373" in next(x for x in lg.assumptions if x.id == "a8").text


def test_air_chargeable_weight_and_minimum():
    # 0.5 kg product -> 0.625 kg gross; 0.01 m³ x 167 = 1.67 kg volumetric wins
    per, label, note = landed.freight_detail("air", 0.5, 0.01, None, 2000)
    assert label == "estimate" and per == pytest.approx(1.67 * 6.0) and "forwarder" in note
    assert landed.freight_detail("express", 0.5, 0.01, None, 2000)[0] == pytest.approx(1.8 * per)
    heavy = landed.freight_detail("air", 2.0, 0.001, None, 100)[0]  # gross 2.5 kg beats 0.167 kg
    assert heavy == pytest.approx(2.5 * 6.0)
    assert landed.freight_detail("air", 0.01, 0.0005, None, 10)[0] == pytest.approx(15.0)  # $150 minimum / 10 units
