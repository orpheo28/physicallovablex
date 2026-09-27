"""Shared bits of the two demo agents: connect to the production MCP over HTTP, call tools, print a readable transcript."""

from __future__ import annotations

import argparse
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

DEFAULT_URL = "http://localhost:8000/mcp"


def parse_args(desc: str) -> argparse.Namespace:
    """Known flags only, so a script can add its own."""
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--url", default=os.getenv("MCP_URL", DEFAULT_URL), help=f"MCP endpoint (env MCP_URL, default {DEFAULT_URL})")
    ap.add_argument("--token", default=os.getenv("MCP_TOKEN", ""), help="bearer token (env MCP_TOKEN; empty = none)")
    return ap.parse_known_args()[0]


@asynccontextmanager
async def connect(url: str, token: str) -> AsyncIterator[Client]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with create_mcp_http_client(headers=headers) as http:
        async with Client(streamable_http_client(url, http_client=http)) as client:
            yield client


def result_data(res: Any) -> Any:
    """Tool result → plain JSON (structured content, else the first text block)."""
    if res.is_error:
        raise RuntimeError(res.content[0].text if res.content else "tool error")
    sc = res.structured_content
    if sc is not None:
        return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
    return json.loads(res.content[0].text)


class Transcript:
    def __init__(self, who: str) -> None:
        self.who = who

    def say(self, text: str) -> None:
        print(f"\n[{self.who}] {text}")

    async def call(self, client: Client, tool: str, **args: Any) -> Any:
        shown = ", ".join(f"{k}={v!r}" for k, v in args.items() if v is not None)
        print(f"\n  → {tool}({shown})")
        data = result_data(await client.call_tool(tool, args))
        return data
