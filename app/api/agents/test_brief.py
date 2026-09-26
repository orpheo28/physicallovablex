import pytest
from contracts.artifacts import BriefArtifact
from pydantic import ValidationError

from api.agents import brief as B
from api.llm import LLMError, LLMValidationError
from api.stages.registry import StageContext


def draft(**kw):
    base = dict(
        product_name="Tracker Card", one_liner="A wallet-thin BLE tracker.", category="ble_accessory", target_markets=["US"],
        target_price_value=29.0, target_price_currency="USD", price_from_prompt=False, key_features=["BLE finding", "Thin"],
        constraints=[], has_battery=True, wireless=["BLE"],
        questions=[{"id": "q1", "topic": "markets", "question": "Markets?", "options": ["US", "EU"], "default": "US"},
                   {"id": "q2", "topic": "volume", "question": "Volume?", "options": ["500", "2,000"], "default": "2,000"}],
    )  # fmt: skip
    base.update(kw)
    return B.BriefDraft.model_validate(base)


def ctx_for(project, inputs=None, **proj):
    p = project.model_copy(update={"example": None, **proj})
    return StageContext(project=p, stage=1, inputs=inputs or {})


def test_idea_mode_defaults_skip(monkeypatch, project):
    monkeypatch.setattr(B, "complete_json", lambda *a, **k: draft())
    art = B.run_brief(ctx_for(project))
    BriefArtifact.model_validate(art.model_dump())
    assert art.category in B.CATEGORIES and art.generated_by.startswith("llm:")
    assert 1 <= len(art.clarifying_questions) <= 5
    assert {q.topic for q in art.clarifying_questions} == set(B.TOPICS)
    assert all(q.skipped and q.answer for q in art.clarifying_questions)  # every question has a default
    assert art.target_volumes == [500, 2000, 10000] and art.target_retail_price.label == "estimate"


def test_answers_applied(monkeypatch, project):
    monkeypatch.setattr(B, "complete_json", lambda *a, **k: draft())
    art = B.run_brief(ctx_for(project, {"answers": {"q1": "US + EU + UK", "q2": "5,000", "q3": "€39", "q4": "None", "q5": "None"}}))
    assert art.target_markets == ["US", "EU", "UK"]
    assert 5000 in art.target_volumes
    assert (art.target_retail_price.value, art.target_retail_price.unit) == (39.0, "EUR")
    assert art.has_battery is False and art.wireless == []
    assert not any(q.skipped for q in art.clarifying_questions)


def test_prototype_mode_parses_bom(monkeypatch, project):
    bom = "part,qty,mpn\nnRF52832 BLE module,1,NRF52832-QFAA\nLi-ion cell 18650,1,C725790\nSilicone foot,4,\nRetail box,1,"
    monkeypatch.setattr(B, "complete_json", lambda *a, **k: draft())
    art = B.run_brief(ctx_for(project, mode="prototype", pasted_bom=bom))
    by_part = {b.part: b for b in art.pasted_bom}
    assert by_part["nRF52832 BLE module"].category == "electronic" and by_part["nRF52832 BLE module"].manufacturer_pn == "NRF52832-QFAA"
    assert by_part["Li-ion cell 18650"].lcsc_pn == "C725790"
    assert by_part["Silicone foot"].qty == 4 and by_part["Silicone foot"].category == "mechanical"
    assert by_part["Retail box"].category == "packaging"


def test_free_text_bom():
    items = B.parse_pasted_bom("2x LED white 2835\nUSB-C receptacle x1\nfoo")
    assert [(i.part, i.qty) for i in items][:2] == [("LED white 2835", 2.0), ("USB-C receptacle", 1.0)]
    assert B.parse_pasted_bom("") == [] and B.parse_pasted_bom(None) == []


def test_at_most_five_questions(monkeypatch, project):
    qs = [{"id": f"x{i}", "topic": t, "question": "?", "default": "d"} for i, t in enumerate(["markets", "volume", "target_price", "battery", "wireless", "other", "other"])]
    monkeypatch.setattr(B, "complete_json", lambda *a, **k: draft(questions=qs))
    assert len(B.run_brief(ctx_for(project)).clarifying_questions) == 5


@pytest.mark.parametrize("exc", [LLMError("main", "boom"), LLMValidationError("main", "bad json"), RuntimeError("x")])
def test_llm_failure_raises(monkeypatch, project, exc):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(B, "complete_json", boom)
    with pytest.raises(Exception):
        B.run_brief(ctx_for(project))


def test_invalid_json_from_model_raises(monkeypatch, project):
    import api.llm as llm

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("LLM_MAIN_MODEL", "fake/model")
    monkeypatch.setattr(llm, "_call", lambda *a, **k: "this is not json")
    with pytest.raises(llm.LLMValidationError):
        B.run_brief(ctx_for(project))


def test_no_key_raises_not_configured(project):
    from api.llm import LLMNotConfigured

    with pytest.raises(LLMNotConfigured):
        B.run_brief(ctx_for(project))


def test_render_prompt_accepts_name_placeholder(monkeypatch, project):
    """Regression (W7 fix a): a `name=` placeholder must never collide with the template argument."""
    from api.agents._common import render_prompt

    text = render_prompt("brief", name="Lumo", prompt="p", mode="idea", bom=[], answers={})
    assert "Lumo" in text and "{{name}}" not in text
    seen = {}
    monkeypatch.setattr(B, "complete_json", lambda route, prompt, schema, **k: seen.setdefault("p", prompt) and draft())
    B.run_brief(ctx_for(project, name="Lumo lamp"))
    assert "Lumo lamp" in seen["p"]


def test_pasted_bom_keeps_prices_and_classifies_afe():
    """W7 (prompt 7): the pasted BOM's unit prices survive as Estimates; an optical AFE is electronic."""
    items = B.parse_pasted_bom("Part,Qty,Unit price (USD),Note\nMAX86141 optical AFE (PPG),1,2.10,heart rate\nTitanium shell,1,4.50,sizes 6-12\n")
    afe, shell = items
    assert afe.category == "electronic" and afe.unit_cost_est.value == 2.10 and afe.unit_cost_est.label == "estimate"
    assert shell.category == "mechanical" and shell.unit_cost_est.value == 4.50 and afe.description == "heart rate"
