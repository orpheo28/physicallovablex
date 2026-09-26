"""W9: shared-password gate, per-IP live-run limit, DEMO_READONLY. Env is read per request, so monkeypatch is enough."""

import pytest
from fastapi.testclient import TestClient

from api import auth
from api.main import app

client = TestClient(app)
BODY = {"mode": "idea", "prompt": "desk lamp"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for k in ("API_SHARED_KEY", "DEMO_READONLY", "RATE_LIMIT_PER_DAY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    auth.reset_rate_limits()


def test_open_when_no_password():
    assert client.get("/projects").status_code == 200
    assert client.get("/health").status_code == 200


def test_password_gate(monkeypatch):
    monkeypatch.setenv("API_SHARED_KEY", "s3cret")
    assert client.get("/health").status_code == 200  # health stays public
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers={"X-App-Key": "wrong"}).status_code == 401
    assert client.get("/projects", headers={"X-App-Key": "s3cret"}).status_code == 200
    assert client.post("/demo/reset").status_code == 401
    assert client.get("/files/demo_desk_lamp/enclosure.glb").status_code == 401  # files protected too
    assert client.get("/files/x/y.glb", headers={"X-App-Key": "s3cret"}).status_code == 404  # passes the gate
    assert client.post("/projects", json={"prompt": "lamp"}).status_code == 401


def test_cors_preflight_and_401_have_cors_headers(monkeypatch):
    monkeypatch.setenv("API_SHARED_KEY", "s3cret")
    h = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "x-app-key"}
    r = client.options("/projects", headers=h)
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:3000"
    r = client.get("/projects", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 401 and r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_rate_limit_only_with_live_key(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_DAY", "2")
    for _ in range(4):  # no key → fixtures, free → never limited
        assert client.post("/projects", json=BODY).status_code == 201
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    h = {"X-Forwarded-For": "1.2.3.4"}
    assert client.post("/projects", json=BODY, headers=h).status_code == 201
    assert client.post("/projects", json=BODY, headers=h).status_code == 201
    r = client.post("/projects", json=BODY, headers=h)
    assert r.status_code == 429 and "Daily limit" in r.json()["detail"] and "retry-after" in r.headers
    assert client.get("/projects", headers=h).status_code == 200  # reads are never limited
    assert client.post("/projects", json=BODY, headers={"X-Forwarded-For": "5.6.7.8"}).status_code == 201


def test_rate_limit_window():
    assert auth.rate_limit_left("ip", 1, now=0) is None
    assert auth.rate_limit_left("ip", 1, now=10) == auth.WINDOW_S - 10 + 1
    assert auth.rate_limit_left("ip", 1, now=auth.WINDOW_S + 1) is None


def test_demo_readonly(monkeypatch):
    client.post("/demo/reset")
    monkeypatch.setenv("DEMO_READONLY", "1")
    for path in ("/projects", "/projects/demo_desk_lamp/stages/3/run", "/projects/demo_desk_lamp/autorun"):
        r = client.post(path, json={"prompt": "x"})
        assert r.status_code == 403 and "Read-only" in r.json()["detail"], path
    assert client.post("/factories", json={}).status_code == 403
    assert client.get("/projects/demo_desk_lamp").status_code == 200
    assert client.get("/projects/demo_desk_lamp/stages/5").status_code == 200
    assert client.get("/projects/demo_desk_lamp/export").status_code == 200
    assert client.get("/factories").status_code == 200


def test_seed_on_empty(monkeypatch):
    from api import db

    db.reset_db()
    monkeypatch.setenv("SEED_DEMO_ON_EMPTY", "1")
    with TestClient(app) as c:
        ids = {p["id"] for p in c.get("/projects").json()}
        assert {"demo_desk_lamp", "demo_tracker_card"} <= ids
    n = len(ids)
    with TestClient(app) as c:  # non-empty DB is left alone
        assert len(c.get("/projects").json()) == n


def test_prune_keeps_most_recent(tmp_path, monkeypatch):
    import os

    from api.housekeeping import prune_files

    monkeypatch.setenv("FILES_DIR", str(tmp_path))
    for i in range(5):
        d = tmp_path / f"p_{i}"
        d.mkdir()
        (d / "a.glb").write_bytes(b"x")
        os.utime(d, (1000 + i, 1000 + i))
    (tmp_path / "demo_keep").mkdir()
    assert sorted(prune_files(2)) == ["p_0", "p_1", "p_2"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["demo_keep", "p_3", "p_4"]
