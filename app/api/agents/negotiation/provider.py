"""Factory portal backend (W5): GET /factories, /factories/{id}, /factories/{id}/rfqs read the MCP network store."""

from __future__ import annotations

from api.stages.registry import provider
from factory_mcp.network import FactoryNetwork


@provider("network")
def network_provider() -> FactoryNetwork:
    return FactoryNetwork()
