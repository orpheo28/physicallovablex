"""C4: curated example library + BM25 retrieval behind CODEGEN_RAG (LLM mocked; no key in the test session)."""

import json

import pytest

from api.cad.codegen import check_code, generate_cad, retrieval
from api.cad.codegen.engine import RAG_RULES, SYSTEM, _gen_prompt, _seed, repair_hints, system_prompt
from api.cad.codegen.library import INDEX, load_examples, parse_header

GOOD = '''import math
from build123d import *

P = {"length": 60.0, "width": 40.0, "height": 20.0}


def build():
    body = Box(P["length"], P["width"], P["height"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = "body.1"
    return [body]
'''
BAD = GOOD.replace("return [body]", "raise ValueError('Failed creating a fillet with radius of 9')")


class FakeLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, prompt: str, system: str) -> str:
        self.calls.append((prompt, system))
        return f"```python\n{self.replies.pop(0)}```"


@pytest.fixture
def rag_on(monkeypatch):
    monkeypatch.setenv("CODEGEN_RAG", "1")
    yield


# --------------------------------------------------------------------------- library


def test_library_size_and_metadata():
    exs = load_examples()
    assert 60 <= len(exs) <= 120
    ids = [e.id for e in exs]
    assert len(ids) == len(set(ids))
    for e in exs:
        assert e.title and e.description and len(e.tags) >= 4, e.id
    assert {e.family for e in exs if e.source == "seed"} >= {"board", "drone", "camera", "smartphone", "furniture"}


def test_every_example_is_sandbox_legal_and_measured():
    facts = json.loads(INDEX.read_text())
    for e in load_examples():
        assert check_code(e.code) == [], e.id
        assert facts[e.id]["ok"] and len(facts[e.id]["bbox_mm"]) == 3, e.id  # --reindex ran it in the real sandbox


def test_parse_header():
    t, d, tags = parse_header('"""Hinge with pin.\n\nTwo leaves and a pin.\ntags: hinge, pin, Knuckle\n"""\nx = 1\n')
    assert (t, d, tags) == ("Hinge with pin", "Two leaves and a pin.", ["hinge", "pin", "knuckle"])


# --------------------------------------------------------------------------- retrieval


@pytest.mark.parametrize("query,needle", [
    ("Stainless butt hinge with alternating knuckles and a pin", "hinge"),
    ("Screw cap with an internal thread and grip ribs", "cap"),
    ("Spur gear with 24 teeth, a bore and a keyway", "gear"),
    ("Curved cabinet pull handle swept along an arc", "handle"),
    ("Fan grille plate with a grid of vent slots", "vent"),
    ("Battery compartment door with a latch", "battery"),
    ("M20 cable gland with a domed cap nut", "gland"),
    ("Foldable quadcopter drone with gimbal camera", "drone"),
])
def test_retrieval_finds_relevant_examples(query, needle):
    top = [e.id for e, _ in retrieval.retrieve(query, k=4)]
    assert top and any(needle in i for i in top[:3]), (query, top)


def test_retrieval_excludes_seed_family_and_dedups_variants():
    ids = [e.id for e, _ in retrieval.retrieve("camera drone with propellers and a gimbal", k=5, exclude_family="drone")]
    assert not any(i.startswith("seed_drone") for i in ids)
    fams = [e.family for e, _ in retrieval.retrieve("surfboard kiteboard board fins", k=5) if e.family]
    assert len(fams) == len(set(fams))


def test_retrieval_nothing_for_noise():
    assert retrieval.retrieve("qwxz blorf") == []
    assert retrieval.examples_block("qwxz blorf") == ""


@pytest.mark.parametrize("budget", [3000, 6000, 9000])
def test_examples_block_bounded(budget):
    block = retrieval.examples_block("rounded enclosure with vent slots, screw bosses and a battery door", budget_chars=budget)
    assert block and len(block) <= budget + 400  # + the fixed header sentence
    assert 1 <= len(retrieval.last_ids(block)) <= 4


def test_full_prompt_size_bounded(rag_on):
    for brief in ("Foldable camera drone", "Butt hinge with a pin", "Retro instant camera with flash"):
        fam = None if "hinge" in brief else ("drone" if "drone" in brief else "camera")
        seed, name = _seed(fam, None)
        p = _gen_prompt(brief, "", "x", (100, 100, 50), seed, name) + "\n\n" + retrieval.examples_block(brief, exclude_family=name)
        assert len(p) < 20_000 and len(SYSTEM + RAG_RULES) < 7_000


# --------------------------------------------------------------------------- engine flag


def test_flag_off_prompts_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEGEN_RAG", raising=False)
    llm = FakeLLM(GOOD)
    r = generate_cad("Butt hinge with a pin", out_dir=tmp_path, llm=llm, dims=(60, 40, 20))
    assert r["status"] == "ok" and "rag" not in r
    prompt, system = llm.calls[0]
    seed, name = _seed(None, None)
    assert system == system_prompt()  # C5: SYSTEM (+ stdparts snippet at pro)
    assert prompt == _gen_prompt("Butt hinge with a pin", "", r["category"], (60.0, 40.0, 20.0), seed, name)


def test_flag_off_repair_prompt_has_no_hints(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEGEN_RAG", "0")
    llm = FakeLLM(BAD, GOOD)
    r = generate_cad("Box", out_dir=tmp_path, llm=llm, dims=(60, 40, 20))
    assert r["status"] == "repaired" and "Likely fix" not in llm.calls[1][0]


def test_flag_on_adds_examples_rules_and_hints(tmp_path, rag_on):
    llm = FakeLLM(BAD, GOOD)
    r = generate_cad("Stainless butt hinge with knuckles and a pin", out_dir=tmp_path, llm=llm, dims=(60, 40, 20))
    assert r["status"] == "repaired"
    (p1, s1), (p2, s2) = llm.calls
    assert s1 == system_prompt() + RAG_RULES == s2
    assert "Reference idioms" in p1 and r["rag"]["examples"]
    assert any("hinge" in i for i in r["rag"]["examples"])
    assert "Likely fix" in p2 and "fillet" in p2.split("Likely fix")[1]


def test_flag_on_edit_mode_smaller_block(tmp_path, rag_on):
    llm = FakeLLM(GOOD, GOOD)
    generate_cad("Desk hub enclosure", out_dir=tmp_path, llm=llm, dims=(60, 40, 20))
    r = generate_cad("Desk hub enclosure", previous_code=GOOD, instruction="add a row of vent slots on top",
                     out_dir=tmp_path, llm=llm, dims=(60, 40, 20))
    assert r["status"] == "ok" and len(r["rag"]["examples"]) <= 2


def test_repair_hints():
    assert "RectangleRounded" in repair_hints("ValueError: width and height must be > 2*radius")
    assert "Scale" in repair_hints("Validation failed: Measured bounding box [1, 2, 3] mm is outside 0.5×–2×")
    assert repair_hints("something unrelated") == ""
