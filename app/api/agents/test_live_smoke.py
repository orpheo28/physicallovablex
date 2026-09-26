"""One tiny live call per configured route. Skipped without OPENROUTER_API_KEY. Never prints the key."""

import pytest
from pydantic import BaseModel

from api import llm
from api.agents.conftest import REAL_KEY

pytestmark = pytest.mark.live


class Pong(BaseModel):
    ok: bool


@pytest.mark.parametrize("route", ["main", "fast", "cn"])
def test_live_route(route, monkeypatch):
    if not REAL_KEY:
        pytest.skip("no OPENROUTER_API_KEY")
    monkeypatch.setenv("OPENROUTER_API_KEY", REAL_KEY)
    if not llm.model_for(route):
        pytest.skip(f"no model configured for route {route}")
    out = llm.complete_json(route, 'Reply with {"ok": true}.', Pong, max_tokens=60, temperature=0)
    assert out.ok is True
