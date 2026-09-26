import pytest
from contracts.artifacts import DFMIssue

from api.agents import dfm_review as D
from api.llm import LLMError


def test_no_key_returns_checklist(lamp):
    spec = lamp[3]
    issues = D.ai_review(spec, spec.bom, [])
    assert len(issues) >= 3
    ids = {p.id for p in spec.parts}
    for i in issues:
        DFMIssue.model_validate(i.model_dump())
        assert i.method == "ai_reviewed" and i.measurement is None
        assert i.fix and i.rule_citation and (i.part_id is None or i.part_id in ids)
    assert len({i.id for i in issues}) == len(issues)
    assert any(i.severity == "critical" and "62133" in i.rule_citation for i in issues)  # battery safety


def test_measured_findings_are_not_contradicted(lamp):
    spec = lamp[3]
    measured = [i for i in lamp[4].issues if i.method == "measured"]
    issues = D.ai_review(spec, spec.bom, measured)
    keys = {(m.part_id, m.category) for m in measured}
    assert not [i for i in issues if (i.part_id, i.category) in keys]


def test_llm_output_filtered(monkeypatch, lamp):
    spec = lamp[3]
    measured = [i for i in lamp[4].issues if i.method == "measured"]
    m0 = measured[0]
    good = dict(severity="minor", category="assembly", part_id="p1", description="Magnet press-fit needs a lead-in.", fix="Add 0.5 mm chamfer.", rule_citation="Press-fit lead-in — DFA guidance")
    drafts = [
        good,
        dict(good, category=m0.category, part_id=m0.part_id),  # duplicates a measured finding → dropped
        dict(good, part_id="p99"),  # unknown part → dropped
        dict(good, rule_citation=""),  # no citation → dropped
    ]
    monkeypatch.setattr(D, "complete_json", lambda *a, **k: D._ReviewDraft.model_validate({"issues": drafts}))
    issues = D.ai_review(spec, spec.bom, measured)
    descs = [i.description for i in issues]
    assert descs.count("Magnet press-fit needs a lead-in.") == 1
    assert not [i for i in issues if i.part_id == "p99"]
    assert any(i.severity == "critical" for i in issues)  # battery issue enforced in code


@pytest.mark.parametrize("exc", [LLMError("main", "x"), ValueError("bad"), RuntimeError("net")])
def test_llm_failure_falls_back(monkeypatch, lamp, exc):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(D, "complete_json", boom)
    assert D.ai_review(lamp[3], lamp[3].bom, []) 


def test_wall_out_of_range(lamp):
    spec = lamp[3].model_copy(deep=True)
    spec.parts[0].wall_thickness.value = 6.0
    issues = D.checklist_review(spec, spec.bom, [])
    assert any(i.category == "wall_thickness" and i.part_id == "p1" and "outside" in i.description for i in issues)


def test_ai_never_reports_geometry_when_measured(monkeypatch, lamp):
    """W7 fix b: measured findings exist → AI draft/undercut/projection issues are dropped (LLM and checklist)."""
    spec = lamp[3]
    measured = [i for i in lamp[4].issues if i.method == "measured"]
    assert measured
    base = dict(severity="major", part_id=None, description="x", fix="y", rule_citation="z")
    other_part = next(p.id for p in spec.parts if p.id not in {m.part_id for m in measured})
    drafts = [dict(base, category="undercut", part_id=other_part), dict(base, category="draft"),
              dict(base, category="projection"), dict(base, category="assembly")]
    monkeypatch.setattr(D, "complete_json", lambda *a, **k: D._ReviewDraft.model_validate({"issues": drafts}))
    issues = D.ai_review(spec, spec.bom, measured)
    assert not [i for i in issues if i.category in D.GEOMETRY_CATEGORIES]
    assert any(i.category == "assembly" for i in issues)
    # deterministic checklist path too
    assert not [i for i in D.checklist_review(spec, spec.bom, measured) if i.category in D.GEOMETRY_CATEGORIES]
