"""W7f: GET /projects/{id} must stay fast while a (slow, live-like) background autorun runs.

Real uvicorn server in a thread (same event loop + threadpool as production). Every LLM call (complete_json,
complete_text) and the image call are mocked with a sleep, then fail like a provider would → the live code paths run
(defaults, template BOM, measured DFM, cost engine, matching). Polls every 0.5 s must answer in < 1 s and show progress.
"""

import sys
import threading
import time

import httpx
import pytest

SLEEP_S = 1.5


@pytest.fixture
def server(monkeypatch):
    import uvicorn

    import api.cad.renders as renders
    import api.llm as llm
    from api.main import app

    for k, v in {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_MAIN_MODEL": "m/main", "LLM_FAST_MODEL": "m/fast",
                 "LLM_CN_MODEL": "m/cn", "LLM_IMAGE_MODEL": "m/image", "API_SHARED_KEY": "", "RATE_LIMIT_PER_DAY": "0"}.items():
        monkeypatch.setenv(k, v)

    def slow(*_a, **_k):
        time.sleep(SLEEP_S)
        raise llm.LLMError("main", "mocked slow provider failure")

    def slow_image(*_a, **_k):
        time.sleep(SLEEP_S)
        raise RuntimeError("mocked slow image failure")

    monkeypatch.setattr(llm, "complete_json", slow)
    monkeypatch.setattr(llm, "complete_text", slow)
    monkeypatch.setattr(renders, "_call", slow_image)
    for name, mod in list(sys.modules.items()):  # modules that did `from api.llm import complete_json`
        if name.startswith("api.") and mod is not llm and getattr(mod, "complete_json", None) is not None:
            monkeypatch.setattr(mod, "complete_json", slow)

    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    port = srv.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(10)


def test_polling_stays_fast_during_background_autorun(server):
    c = httpx.Client(base_url=server, timeout=5)
    pid = c.post("/projects", json={"mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"}).json()["id"]
    assert c.post(f"/projects/{pid}/autorun").status_code == 202
    latencies, seen_stages, state = [], set(), "running"
    t0 = time.time()
    while state == "running" and time.time() - t0 < 180:
        s = time.perf_counter()
        r = c.get(f"/projects/{pid}")
        latencies.append(time.perf_counter() - s)
        assert r.status_code == 200
        auto = r.json()["autorun"]
        state = auto["state"]
        if auto["current_stage"]:
            seen_stages.add(auto["current_stage"])
        # other reads the web app does meanwhile
        assert c.get("/factories").status_code == 200
        time.sleep(0.5)
    assert state == "done", state
    assert max(latencies) < 1.0, f"slowest poll {max(latencies):.2f} s"
    assert len(seen_stages) >= 3, seen_stages  # progress visible while running
    assert len(latencies) >= 8


def test_files_consistent_while_republished(server):
    """W7f: a GLB republished by stage 2/3 while the viewer downloads it: every response is complete (body length =
    Content-Length) and fast. Before: shutil.copyfile / in-place save + FileResponse could send a truncated body with
    the old Content-Length, which leaves a proxied browser request hanging and starves the polling connection."""
    import os
    import random

    from api.cad.build import files_root, publish

    pid = "p_publishtest"
    d = files_root() / pid
    d.mkdir(parents=True, exist_ok=True)
    srcs = []
    for i, size in enumerate((300_000, 900_000)):
        p = d / f".src{i}"
        p.write_bytes(os.urandom(size))
        srcs.append(p)
    publish(srcs[0], d / "d1.glb")
    stop = False

    def writer():
        while not stop:
            publish(random.choice(srcs), d / "d1.glb")

    th = threading.Thread(target=writer, daemon=True)
    th.start()
    try:
        c = httpx.Client(base_url=server, timeout=5)
        for _ in range(60):
            s = time.perf_counter()
            r = c.get(f"/files/{pid}/d1.glb")
            assert r.status_code == 200 and len(r.content) == int(r.headers["content-length"]) in (300_000, 900_000)
            assert time.perf_counter() - s < 1.0
    finally:
        stop = True
        th.join(5)
