import os
import tempfile
from pathlib import Path

# Isolated DB + CAD files dir + no LLM key for the test session (fixture-only flow).
# The root conftest.py sets the same variables for the whole suite; these defaults cover `pytest tests/` alone.
_tmp = Path(tempfile.mkdtemp())
os.environ.setdefault("DB_PATH", str(_tmp / "test.db"))
os.environ.setdefault("FILES_DIR", str(_tmp / "files"))
os.environ["OPENROUTER_API_KEY"] = ""
