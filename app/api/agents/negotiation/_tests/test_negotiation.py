"""Stages 7-8 + factory portal, offline (no key → scripted agents, still live: fallback false)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.stages import runner
from contracts.artifacts import MatchingArtifact, NegotiationArtifact, Project, QuoteStatus, StageStatus
from factory_mcp import network

client = TestClient(app)


def _project(pid: str) -> str:
    runner.save_project(Project(id=pid, name="Desk lamp test", mode="idea", prompt="desk lamp", example="desk_lamp"))
    for n in range(1, 7):
        runner.save_artifact(pid, n, runner.load_fixture("desk_lamp", n, pid), StageStatus.validated)
    runner.get_factory_pack(pid, rebuild=True)
    return pid


@pytest.fixture(scope="module")
def pid():
    network.reset()
    return _project("p_w5_test")


def test_stage7_live_deterministic(pid):
    a = runner.run_stage(pid, 7)
    assert isinstance(a, MatchingArtifact) and a.fallback is False, a.fallback_reason
    MatchingArtifact.model_validate(a.model_dump())
    assert a.generated_by == "code"
    assert len(a.shortlist) >= 3
    assert {q.process for q in a.queries} >= {"injection_molding", "pcba", "assembly"}
    for m in a.shortlist:
        assert m.reasons and all(r.strip() for r in m.reasons)
        assert network.get_factory(m.factory_id).name == m.factory_name
    b = runner.run_stage(pid, 7)
    assert [(m.factory_id, m.score.value) for m in a.shortlist] == [(m.factory_id, m.score.value) for m in b.shortlist]


def test_stage8_live_scripted(pid):
    a = runner.run_stage(pid, 8)
    assert isinstance(a, NegotiationArtifact) and a.fallback is False, a.fallback_reason
    NegotiationArtifact.model_validate(a.model_dump())
    assert a.generated_by == "code" and a.user_approved is False and a.final_terms is None
    shortlist = [m.factory_id for m in runner.get_artifact(pid, 7).shortlist[:3]]
    assert [r.factory_id for r in a.rfqs] == shortlist
    speakers = {t.speaker for t in a.transcript}
    assert {"platform_agent", "factory_agent"} <= speakers
    assert [t.turn for t in a.transcript] == list(range(1, len(a.transcript) + 1))
    for r in a.rfqs:
        counters = [t for t in a.transcript if t.rfq_id == r.id and t.speaker == "platform_agent" and t.proposed_changes]
        assert 1 <= len(counters) <= 2
        assert any(q.rfq_id == r.id for q in a.quotes)
    assert a.recommendation.quote_id in {q.id for q in a.quotes}
    assert a.recommendation.rationale
    # quotes anchored on stage 5 (desk lamp 2,000-unit ex-works estimate $12.50) within personality bands
    for q in a.quotes:
        p2000 = next(t.unit_price_usd for t in q.tiers if t.quantity == 2000)
        assert 10.5 < p2000 < 16.5
    assert all(q.label == "fictional" for q in a.quotes)


def test_stage8_approval_sets_final_terms(pid):
    before = runner.get_artifact(pid, 8)
    a = runner.run_stage(pid, 8, {"approve": True})
    assert a.fallback is False, a.fallback_reason
    assert a.user_approved is True and a.final_terms is not None
    ft = a.final_terms
    assert ft.quote_id == before.recommendation.quote_id
    assert ft.unit_price.label == "fictional" and ft.tooling.label == "fictional" and ft.lead_time_days.label == "fictional"
    assert ft.quantity >= ft.moq
    assert network.get_quote(ft.quote_id).status == QuoteStatus.accepted
    assert a.transcript[-2].speaker == "user"
    assert [r.id for r in a.rfqs] == [r.id for r in before.rfqs]  # approval does not re-negotiate


def test_stage8_approval_of_explicit_quote():
    pid = _project("p_w5_explicit")
    runner.run_stage(pid, 7)
    neg = runner.run_stage(pid, 8)
    other = [q for q in neg.quotes if q.factory_id != neg.recommendation.factory_id][-1]
    a = runner.run_stage(pid, 8, {"approve": True, "quote_id": other.id})
    assert a.fallback is False and a.final_terms.quote_id == other.id and a.final_terms.factory_id == other.factory_id


def test_factory_portal_routes(pid):
    fs = client.get("/factories").json()
    assert len(fs) == 15 and all(f["name"].endswith("(fictional)") for f in fs)  # 8 + 3 installers (W20) + 3 (W21) + 1 (W21b)
    neg = runner.get_artifact(pid, 8)
    for rfq in neg.rfqs:
        r = client.get(f"/factories/{rfq.factory_id}/rfqs")
        assert r.status_code == 200
        items = {x["rfq"]["id"]: x for x in r.json()}
        assert rfq.id in items and items[rfq.id]["quotes"]
    assert client.get("/factories/nope/rfqs").status_code == 404


def test_api_run_stage_7_and_8():
    pid = _project("p_w5_api")
    r7 = client.post(f"/projects/{pid}/stages/7/run", json={"inputs": {}})
    assert r7.status_code == 200 and r7.json()["fallback"] is False
    r8 = client.post(f"/projects/{pid}/stages/8/run", json={"inputs": {}})
    assert r8.status_code == 200 and r8.json()["fallback"] is False
    ok = client.post(f"/projects/{pid}/stages/8/run", json={"inputs": {"approve": True}}).json()
    assert ok["fallback"] is False and ok["artifact"]["user_approved"] and ok["artifact"]["final_terms"]


def test_stage8_llm_path_is_clamped(monkeypatch):
    """With a (fake) model: agents' wording is used, numbers stay within the policy bands, generated_by llm:<slug>."""
    from api import llm
    from api.agents.negotiation import rfq as rfq_mod

    def fake(route, prompt, schema, **kw):
        if schema is rfq_mod.FactoryQuoteDraft:
            return schema(message="We can do it.", unit_prices=[1.0, 99.0, 5.0], tooling_usd=1.0, lead_time_days=400,
                          payment_terms="30% deposit / 70% before shipment", exceptions=["Colour matching extra"])
        if schema is rfq_mod.NegotiationPlan:
            ids = [line.split(" ")[1] for line in prompt.splitlines() if line.startswith("- ")]
            return schema(counters=[rfq_mod.CounterDraft(factory_id=i, message="Please sharpen.", rationale="Competing quote.", unit_price_pct=-50) for i in ids])
        if schema is rfq_mod.RecommendationDraft:
            return schema(factory_id="not-a-factory", rationale="x")
        if schema is rfq_mod.CnBatch:
            n = sum(1 for line in prompt.splitlines() if line[:1].isdigit())
            return schema(translations=["中文"] * n)
        raise AssertionError(schema)

    monkeypatch.setattr(llm, "complete_json", fake)
    monkeypatch.setattr(llm, "model_for", lambda route: f"test/{route}-model")
    pid = _project("p_w5_llm")
    runner.run_stage(pid, 7)
    a = runner.run_stage(pid, 8)
    assert a.fallback is False, a.fallback_reason
    assert a.generated_by == "llm:test/main-model"
    assert any(t.message == "We can do it." for t in a.transcript)
    assert any(t.message == "Please sharpen." and t.proposed_changes["unit_price_pct"] == -8.0 for t in a.transcript)
    assert all(t.message_cn == "中文" for t in a.transcript if t.speaker == "platform_agent")
    for q in a.quotes:
        prices = [t.unit_price_usd for t in sorted(q.tiers, key=lambda t: t.quantity)]
        assert prices == sorted(prices, reverse=True)
        assert 9.0 < prices[1] < 17.0 and q.lead_time_days < 60 and q.tooling_usd > 5000
    assert a.recommendation.quote_id in {q.id for q in a.quotes}  # invalid LLM pick → policy pick
