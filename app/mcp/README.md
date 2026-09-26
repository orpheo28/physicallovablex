# mcp/

**Owner: W5 — MCP + Negotiation.**

The production MCP server lives in **[`factory_mcp/`](../factory_mcp/README.md)** (top-level package), not here:
a package inside `mcp/` would shadow the installed `mcp` SDK, and plug-in discovery only scans `api/`.
Run it with `uv run python -m factory_mcp.server` (stdio). Stage 7/8 handlers and the factory-portal
`network` provider are in `api/agents/negotiation/`.

**Do not add an `__init__.py` here**: this folder must stay a plain directory so `import mcp` resolves to the SDK.
