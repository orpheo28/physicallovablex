"""W7d: an exhausted key (HTTP 402), a key cap or a rate limit (429) anywhere → cached fixtures, never a 5xx."""

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

import api.cad.renders as renders
import api.llm as llm
from api.main import app

client = TestClient(app)


class _Failing:
    def __init__(self, status: int):
        self.status = status
        self.chat = self
        self.completions = self
        self.calls = 0

    def with_options(self, **_):
        return self

    def create(self, **_):
        self.calls += 1
        resp = httpx.Response(self.status, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
        raise openai.APIStatusError(f"Error code: {self.status} - Insufficient credits", response=resp, body=None)


@pytest.mark.parametrize("status", [402, 429])
def test_provider_errors_fall_back_everywhere(monkeypatch, status):
    for k, v in {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_MAIN_MODEL": "m/main", "LLM_FAST_MODEL": "m/fast",
                 "LLM_CN_MODEL": "m/cn", "LLM_IMAGE_MODEL": "m/image"}.items():
        monkeypatch.setenv(k, v)
    failing = _Failing(status)
    monkeypatch.setattr(llm, "_client", lambda *a, **k: failing)
    monkeypatch.setattr(renders, "_client", lambda *a, **k: failing)

    pid = client.post("/projects", json={"mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"}).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?wait=true")
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert [x["stage"] for x in results] == [1, 2, 3, 4, 5, 6, 7]
    assert results[0]["fallback"] is True and str(status) in results[0]["artifact"]["fallback_reason"]
    for n in (8,):
        assert client.post(f"/projects/{pid}/stages/{n}/run", json={"inputs": {}}).status_code == 200
    assert client.post(f"/projects/{pid}/stages/8/run", json={"inputs": {"approve": True}}).status_code == 200
    for n in range(9, 14):
        body = client.post(f"/projects/{pid}/stages/{n}/run", json={"inputs": {}})
        assert body.status_code == 200, (n, body.text)
    assert client.post(f"/projects/{pid}/stages/2/render", params={"direction_id": "d2"}).status_code == 200
    assert client.get(f"/projects/{pid}/factory-pack").status_code == 200
    pdf = client.get(f"/projects/{pid}/export")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    detail = client.get(f"/projects/{pid}").json()
    # W7g B1: project-level flag + the Factory Pack and the dossier say "Cached example" in plain words
    assert detail["has_fallback"] is True and 1 in detail["fallback_stages"]
    pack = client.get(f"/projects/{pid}/factory-pack", params={"rebuild": True}).json()
    assert pack["cached_note"].startswith("Cached example — AI was unavailable") and 1 in pack["fallback_stages"]
    from tests.test_smoke import pdf_text

    assert b"AI was unavailable" in pdf_text(pdf.content) or b"CACHED EXAMPLE" in pdf_text(pdf.content)
    assert all(s["status"] == "draft" for s in detail["stages"])
    # every LLM-only stage that could not run shows the cached-example banner (fallback flag), none is an error
    assert detail["stages"][0]["fallback"] and detail["stages"][12]["fallback"]
    assert failing.calls < 60  # no retry storm on a credit / rate-limit error
