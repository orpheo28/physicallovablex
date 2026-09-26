import pytest
from contracts.artifacts import Certification

from api.agents import certification as C
from api.llm import LLMError


def standards(certs):
    return " | ".join(c.standard for c in certs)


def test_tracker_card(tracker):
    brief, spec = tracker
    certs = C.certification_map(brief, spec)
    s = standards(certs)
    assert "FCC Part 15C" in s and "UN38.3" in s and "IEC 62133-2" in s
    assert "RED" in s and "RoHS" in s
    for c in certs:
        Certification.model_validate(c.model_dump())
        assert c.cost_est.label == "estimate" and c.cost_est.source_or_assumption
        assert c.lead_time_weeks.unit == "weeks" and c.lead_time_weeks.label == "estimate"


def test_desk_lamp_no_radio(lamp):
    certs = C.certification_map(lamp[1], lamp[3])
    s = standards(certs)
    assert "FCC Part 15B" in s and "15C" not in s and "EMC 2014/30/EU" in s and "UN38.3" in s and "IEC 62133-2" in s
    assert "RED" not in s


def test_food_contact_dog_bowl(tracker):
    brief, spec = tracker
    brief = brief.model_copy(update={"prompt": "Smart dog bowl that weighs food, Wi-Fi", "wireless": ["Wi-Fi"], "has_battery": False, "target_markets": ["US"]})
    spec = spec.model_copy(update={"product_name": "Smart dog bowl", "bom": [b for b in spec.bom if "LiPo" not in b.part]})
    s = standards(C.certification_map(brief, spec))
    assert "FDA food-contact" in s and "FCC Part 15C" in s and "UN38.3" not in s


def test_kids_toy_and_uk(tracker):
    brief, spec = tracker
    brief = brief.model_copy(update={"prompt": "Kids' audio player with NFC figurines", "wireless": ["NFC"], "target_markets": ["US", "EU", "UK"]})
    s = standards(C.certification_map(brief, spec))
    assert "CPSIA" in s and "Toy Safety Directive" in s and "UKCA" in s


def test_coin_cell_uses_primary_standard(tracker):
    brief, spec = tracker
    spec = spec.model_copy(update={"bom": [b.model_copy(update={"part": "CR2032 coin cell"}) if "LiPo" in b.part else b for b in spec.bom]})
    s = standards(C.certification_map(brief, spec))
    assert "UN38.3" in s and "IEC 60086-4" in s and "62133" not in s


def test_non_electronic_returns_something(tracker):
    brief, spec = tracker
    brief = brief.model_copy(update={"prompt": "Portable manual espresso maker, no electronics", "category": "mechanical", "wireless": [], "has_battery": False, "target_markets": ["US"]})
    spec = spec.model_copy(update={"bom": [], "product_name": "Espresso maker"})
    certs = C.certification_map(brief, spec)
    assert certs and "FDA" in standards(certs)


@pytest.mark.parametrize("exc", [LLMError("fast", "x"), ValueError("bad"), RuntimeError("net")])
def test_llm_failure_keeps_rule_core(monkeypatch, tracker, exc):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(C, "complete_json", boom)
    assert "FCC Part 15C" in standards(C.certification_map(*tracker))


def test_llm_nuance_adds_extra_without_duplicates(monkeypatch, tracker):
    draft = C._NuanceDraft.model_validate({"extra": [
        {"market": "EU", "standard": "EN 62479 RF exposure", "applies_because": "Radio near the body", "cost_usd": 800, "lead_time_weeks": 2},
        {"market": "Global", "standard": "UN38.3 (battery)", "applies_because": "dup", "cost_usd": 1, "lead_time_weeks": 1},
    ], "notes": []})  # fmt: skip
    monkeypatch.setattr(C, "complete_json", lambda *a, **k: draft)
    certs = C.certification_map(*tracker)
    assert sum("UN38.3" in c.standard for c in certs) == 1
    extra = next(c for c in certs if "EN 62479" in c.standard)
    assert "LLM-proposed" in extra.cost_est.source_or_assumption


def test_load_cell_is_not_a_battery():
    """W7: 'load cell' (smart dog bowl) must not trigger UN38.3 / IEC 62133."""
    from contracts.artifacts import BOMItem

    from api.agents.dfm_review import has_cell

    assert not has_cell([BOMItem(id="e1", part="Single-point strain-gauge load cell, 5 kg", category="electronic", qty=1)])
    assert has_cell([BOMItem(id="e1", part="Li-Po cell 3.7 V 500 mAh", category="electronic", qty=1)])


def test_fcc_rows_cite_ecfr_and_ce_rows_cite_eur_lex(tracker):
    brief, spec = tracker
    certs = {c.standard.split(" (")[0]: c for c in C.certification_map(brief, spec)}
    fcc = certs["FCC Part 15C"].applies_because
    assert "47 CFR 15.247" in fcc and "https://www.ecfr.gov/current/title-47/section-15.247" in fcc and "retrieved 2026-" in fcc
    assert "47 CFR 15.19" in fcc and "47 CFR 15.109" in fcc
    red = next(c for c in certs.values() if "RED" in c.standard).applies_because
    assert "https://eur-lex.europa.eu/eli/dir/2014/53/oj" in red
    assert "lithium-battery-guidance-document.pdf" in certs["UN38.3"].applies_because
    assert all(c.cost_est.label == "estimate" and c.lead_time_weeks.label == "estimate" for c in certs.values())


def test_fcc_15b_row_cites_part_15_sections(lamp):
    fcc = next(c for c in C.certification_map(lamp[1], lamp[3]) if c.standard.startswith("FCC Part 15B"))
    assert "47 CFR 15.101" in fcc.applies_because and "15.107" in fcc.applies_because and "ecfr.gov" in fcc.applies_because
