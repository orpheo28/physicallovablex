import os
import tempfile
from pathlib import Path

# Isolated network store + no LLM key (never touch factory_mcp/data/network.db or api/data/app.db).
_tmp = Path(tempfile.mkdtemp())
os.environ["FACTORY_MCP_DB"] = str(_tmp / "network.db")
os.environ.setdefault("DB_PATH", str(_tmp / "app.db"))
os.environ["OPENROUTER_API_KEY"] = ""
