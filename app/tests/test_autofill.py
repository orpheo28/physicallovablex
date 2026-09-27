"""W16: POST /projects/{id}/autorun?through=13 (autofill) — stages 1-13, recommended quote auto-approved, Factory Pack built."""

import sys
import threading
import time

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

import api.cad.renders as renders
import api.llm as llm
from api.main import app

client = TestClient(app)
ENV = {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_MAIN_MODEL": "m/main", "LLM_FAST_MODEL": "m/fast",
       "LLM_CN_MODEL": "m/cn", "LLM_IMAGE_MODEL": "m/image", "API_SHARED_KEY": "", "RATE_LIMIT_PER_DAY": "0"}
PROMPT = {"mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"}


def _mock_llm(monkeypatch, delay: float):
    """Every LLM / image call sleeps `delay` then fails like a provider (live code paths, deterministic fallbacks)."""
    calls = []
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)

    def slow(*_a, **_k):
        calls.append(time.time())
        time.sleep(delay)
        raise llm.LLMError("main", "mocked provider failure")

    def slow_image(*_a, **_k):
        calls.append(time.time())
        time.sleep(delay)
        raise RuntimeError("mocked image failure")

    monkeypatch.setattr(llm, "complete_json", slow)
    monkeypatch.setattr(llm, "complete_text", slow)
    monkeypatch.setattr(renders, "_call", slow_image)
    for name, mod in list(sys.modules.items()):
        if name.startswith("api.") and mod is not llm and getattr(mod, "complete_json", None) is not None:
            monkeypatch.setattr(mod, "complete_json", slow)
    return calls


def _assert_autofilled(c, pid):
    detail = c.get(f"/projects/{pid}").json()
    auto = detail["autorun"]
    assert auto["state"] == "done" and auto["through"] == 13 and auto["current_stage"] is None, auto
    assert auto["completed_stages"] == list(range(1, 14)), auto
    assert all(s["status"] == "draft" for s in detail["stages"])
    neg = c.get(f"/projects/{pid}/stages/8").json()["artifact"]
    assert neg["user_approved"] is True and neg["final_terms"]["quote_id"] == neg["recommendation"]["quote_id"]
    a = next(x for x in neg["assumptions"] if x["id"] == "a8_autofill")
    assert a["label"] == "estimate" and a["text"].startswith("Auto-approved in autofill mode")
    assert c.get(f"/projects/{pid}/factory-pack").status_code == 200


def test_through_13_completes_everything(monkeypatch):
    _mock_llm(monkeypatch, 0)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?through=13&wait=true")
    assert r.status_code == 200, r.text
    assert [x["stage"] for x in r.json()["results"]] == list(range(1, 14))
    _assert_autofilled(client, pid)


def test_through_13_async_and_idempotent(monkeypatch):
    _mock_llm(monkeypatch, 0)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?through=13")
    assert r.status_code == 202 and r.json()["autorun"]["through"] == 13
    t0 = time.time()
    while client.get(f"/projects/{pid}").json()["autorun"]["state"] == "running" and time.time() - t0 < 120:
        time.sleep(0.2)
    _assert_autofilled(client, pid)


def test_through_7_unchanged(monkeypatch):
    _mock_llm(monkeypatch, 0)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?wait=true")
    assert [x["stage"] for x in r.json()["results"]] == [1, 2, 3, 4, 5, 6, 7]
    auto = client.get(f"/projects/{pid}").json()["autorun"]
    assert auto["through"] == 7 and auto["completed_stages"] == [1, 2, 3, 4, 5, 6, 7]
    assert client.get(f"/projects/{pid}/stages/8").status_code == 404
    assert client.post(f"/projects/{pid}/autorun?through=9").status_code == 422


class _Failing:
    def __init__(self, status):
        self.status, self.chat, self.completions = status, self, self

    def with_options(self, **_):
        return self

    def create(self, **_):
        resp = httpx.Response(self.status, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
        raise openai.APIStatusError(f"Error code: {self.status} - Insufficient credits", response=resp, body=None)


def test_through_13_with_402_falls_back_never_5xx(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    failing = _Failing(402)
    monkeypatch.setattr(llm, "_client", lambda *a, **k: failing)
    monkeypatch.setattr(renders, "_client", lambda *a, **k: failing)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?through=13&wait=true")
    assert r.status_code == 200, r.text
    assert len(r.json()["results"]) == 13
    _assert_autofilled(client, pid)
    detail = client.get(f"/projects/{pid}").json()
    assert detail["has_fallback"] is True
    assert client.get(f"/projects/{pid}/export").status_code == 200


@pytest.fixture
def server(monkeypatch):
    import uvicorn

    calls = _mock_llm(monkeypatch, 1.5)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}", calls
    srv.should_exit = True
    th.join(10)


def test_polling_stays_fast_during_autofill(server):
    base, calls = server
    c = httpx.Client(base_url=base, timeout=5)
    pid = c.post("/projects", json=PROMPT).json()["id"]
    t0 = time.time()
    assert c.post(f"/projects/{pid}/autorun?through=13").status_code == 202
    latencies, seen, state = [], set(), "running"
    while state == "running" and time.time() - t0 < 300:
        s = time.perf_counter()
        r = c.get(f"/projects/{pid}")
        latencies.append(time.perf_counter() - s)
        assert r.status_code == 200
        auto = r.json()["autorun"]
        state = auto["state"]
        if auto["current_stage"]:
            seen.add(auto["current_stage"])
        time.sleep(0.5)
    wall = time.time() - t0
    print(f"\nAUTOFILL wall={wall:.0f}s llm_calls={len(calls)} (1.5 s each) stages_seen={sorted(seen)}")
    assert state == "done"
    assert max(latencies) < 1.0, f"slowest poll {max(latencies):.2f} s"
    assert len(seen) >= 8
    _assert_autofilled(c, pid)
