"""Root test setup (whole-suite `uv run pytest`): isolated DB, network store, CAD files dir; no LLM key."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="plx-test-"))
os.environ["DB_PATH"] = str(_tmp / "test.db")
os.environ["FACTORY_MCP_DB"] = str(_tmp / "network.db")
os.environ["FILES_DIR"] = str(_tmp / "files")
os.environ["OPENROUTER_API_KEY"] = ""
# a developer .env must not leak deploy guards into the suite
for _k in ("API_SHARED_KEY", "DEMO_READONLY", "SEED_DEMO_ON_EMPTY"):
    os.environ[_k] = ""
os.environ["RATE_LIMIT_PER_DAY"] = "20"
