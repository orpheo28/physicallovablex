# tests/

**Owner: W6 — Fixtures + Export + Tests.** Only this session edits this folder.

pytest suite + `tests/run_prompts.py` (PRD Appendix A). W0 tests: `test_fixtures.py`, `test_api_flow.py`, `test_discovery.py` — keep them passing.

Contracts: `contracts/artifacts.py`, `contracts/api.md`, `contracts/stage_runner.md`, `contracts/fixtures.md`. Never edit `contracts/`, `api/main.py`, `pyproject.toml`, `web/package.json` — send a CONTRACT CHANGE REQUEST to the Monitor.

## W6 additions
- `test_smoke.py` — no key, temp DB: demo reset, both cached examples through 13 stages + factory pack + export, PDF structure (CN font + outline, labels, banners), Factory Pack provider, tracker card consistency and honesty checks.
- `run_prompts.py` — the 10 prompts of PRD Appendix A against a running API: `uv run python tests/run_prompts.py --base-url http://localhost:8106 [--only 1,2,7]`. Writes `tests/results/<timestamp>.md`; exit code ≠ 0 on 5xx, timeout, invalid artifact or empty PDF (fallbacks pass but are counted).
