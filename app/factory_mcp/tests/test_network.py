"""Production network: seed data, deterministic search_capacity, quote lifecycle (offline, temp store)."""

import pytest
from contracts.artifacts import Factory, QuoteStatus, RFQStatus, SearchCapacityQuery

from factory_mcp import network


@pytest.fixture(autouse=True)
def fresh_store():
    network.reset()
    yield


def test_eight_fictional_factories():
    fs = network.list_factories()
    assert len(fs) == 15  # 8 factories + 3 installers (W20, ids i_*) + 3 specialists (W21) + LSR overmolder (W21b)
    assert len({f.id for f in fs}) == 15
    assert {f.kind for f in fs if f.id.startswith("i_")} == {"installer"} and network.get_factory("f_skyforge").kind == "integrator"
    assert network.get_factory("f_orchid").kind == "factory"
    assert sum(1 for f in fs if f.id.startswith("i_")) == 3
    for f in fs:
        Factory.model_validate(f.model_dump())
        assert f.name.endswith("(fictional)"), f.name
        assert f.fictional is True and f.label == "fictional" and f.capacity.label == "fictional"
    # W0's portal ids are kept
    assert {"f_orchid", "f_silverfern", "f_kestrel", "f_basalt"} <= {f.id for f in fs}
    assert len({f.archetype for f in fs}) >= 6


def test_search_capacity_is_deterministic_with_reasons():
    q = SearchCapacityQuery(process="injection_molding", material="PC/ABS (UL94 V-0)", quantity=2000, certifications_required=["ISO 9001"])
    a, b = network.search_capacity(q), network.search_capacity(q)
    assert [m.model_dump(exclude={"score"}) for m in a] == [m.model_dump(exclude={"score"}) for m in b]
    assert [m.rank for m in a] == list(range(1, len(a) + 1))
    assert len(a) >= 3
    scores = [m.score.value for m in a]
    assert scores == sorted(scores, reverse=True)
    for m in a:
        assert m.reasons and all(r.strip() for r in m.reasons)
        assert {c.criterion for c in m.score_breakdown} == {"process_fit", "moq", "certifications", "load", "lead_time"}
        assert m.score.label == "fictional"
        assert abs(m.score.value - 100 * sum(c.score * c.weight for c in m.score_breakdown)) < 0.11
    # factories without the process are excluded (Basalt is metal only)
    assert "f_basalt" not in {m.factory_id for m in a}


def test_search_capacity_penalises_missing_certification_and_moq():
    q = SearchCapacityQuery(process="cnc", material="Aluminium 6061", quantity=200, certifications_required=["IATF 16949"])
    res = {m.factory_id: m for m in network.search_capacity(q)}
    basalt = {c.criterion: c.score for c in res["f_basalt"].score_breakdown}
    lantern = {c.criterion: c.score for c in res["f_littlelantern"].score_breakdown}
    assert basalt["certifications"] == 1.0 and lantern["certifications"] == 0.0
    assert basalt["moq"] < 1.0 and lantern["moq"] == 1.0


def test_register_capacity_then_searchable():
    fid = network.register_capacity("Test Plastics Co", "Foshan, Guangdong", ["extrusion"], ["Aluminium 6063"], 500, ["ISO 9001"], 20, 10000, 30.0)
    f = network.get_factory_profile(fid)
    assert f.name.endswith("(fictional)")
    q = SearchCapacityQuery(process="extrusion", material="Aluminium 6063-T5", quantity=2000)
    assert fid in [m.factory_id for m in network.search_capacity(q)]


def test_quote_lifecycle():
    rfq_id = network.request_quote("f_orchid", "fp_test", [500, 2000], project_id="p_test", product_name="Test lamp")
    q1 = network.get_quote(network.submit_quote(rfq_id, {500: 15.0, 2000: 13.0}, 9000, 1000, 35, "30% deposit / 70% before shipment"))
    assert q1.version == 1 and network.get_rfq(rfq_id).status == RFQStatus.quoted
    q2 = network.counter_offer(q1.id, {"unit_price_pct": -5, "tooling_usd": 8000}, "cheaper competitor")
    assert q2.version == 2 and q2.status == QuoteStatus.countered
    assert q2.tiers[1].unit_price_usd == pytest.approx(12.35)
    assert network.get_quote(q1.id).status == QuoteStatus.superseded
    q3 = network.get_quote(network.submit_quote(rfq_id, {500: 14.5, 2000: 12.6}, 8500, 1000, 35, "30% deposit / 70% before shipment"))
    assert q3.version == 3
    order = network.accept_quote(q3.id)
    assert order.quote_id == q3.id and order.label == "fictional"
    assert network.get_rfq(rfq_id).status == RFQStatus.accepted
    portal = network.list_rfqs("f_orchid")
    mine = [r for r in portal if r.rfq.id == rfq_id][0]
    assert mine.product_name == "Test lamp" and [q.version for q in mine.quotes] == [1, 2, 3]
    with pytest.raises(ValueError):
        network.counter_offer(q3.id, {"unit_price_pct": -1}, "too late")
    with pytest.raises(network.NotFoundError):
        network.request_quote("nope", "fp", [1])
