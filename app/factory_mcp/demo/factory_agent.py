"""Scripted FACTORY agent over the production MCP (HTTP): register capacity → it appears in the portal and in search.

    uv run python -m factory_mcp.demo.factory_agent [--url http://localhost:8000/mcp] [--token …] [--api http://localhost:8000]

Registers "Tidewater Wearables (fictional)" (LSR overmolding + PCBA). Portal check (GET /factories) uses --api and, if the API is
gated, --api-key (env API_SHARED_KEY). Re-running registers another copy (a new factory_id each time); POST /demo/reset clears it.
"""

from __future__ import annotations

import asyncio
import os

import httpx

from factory_mcp.demo._client import Transcript, connect, parse_args
import argparse

CAPACITY = dict(
    name="Tidewater Wearables",
    region="Penang, MY",
    processes=["injection_molding", "pcba", "assembly"],
    materials=["LSR silicone 50 Shore A", "LSR silicone", "PC/ABS", "FR-4"],
    moq=500,
    certifications=["ISO 9001", "ISO 13485"],
    lead_time_days=28,
    monthly_capacity=60000,
    current_load_pct=35,
)


async def main() -> None:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--api", default=None)
    ap.add_argument("--api-key", default=os.getenv("API_SHARED_KEY", ""))
    extra, _ = ap.parse_known_args()
    args = parse_args(__doc__.splitlines()[0])
    api = (extra.api or args.url.rsplit("/mcp", 1)[0]).rstrip("/")
    say = Transcript("factory agent")
    headers = {"X-App-Key": extra.api_key} if extra.api_key else {}

    def portal() -> list[dict]:
        r = httpx.get(f"{api}/factories", headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()

    async with connect(args.url, args.token) as client:
        say.say(f"Connected to {args.url}")
        try:
            before = portal()
            say.say(f"Portal (GET /factories) lists {len(before)} factories before registration")
        except httpx.HTTPError as e:
            before = []
            say.say(f"(portal check skipped: {e})")

        say.say(f"Registering capacity for {CAPACITY['name']} — {', '.join(CAPACITY['processes'])}, MOQ {CAPACITY['moq']}, "
                f"{CAPACITY['lead_time_days']} d lead time, {CAPACITY['current_load_pct']}% loaded")
        fid = (await say.call(client, "register_capacity", **CAPACITY))["factory_id"]
        print(f"     registered: {fid}")

        try:
            after = portal()
            mine = next((f for f in after if f["id"] == fid), None)
            say.say(f"Portal now lists {len(after)} factories; new one visible: "
                    f"{mine['name'] if mine else 'NOT FOUND'}")
        except httpx.HTTPError:
            pass

        say.say("A buyer's agent searches LSR overmolding / 2,000 units / ISO 9001 / before 2026-12-15 — does the new factory rank?")
        matches = await say.call(client, "search_capacity", process="injection_molding", material="LSR silicone", quantity=2000,
                                 certifications_required=["ISO 9001"], deadline="2026-12-15")
        for m in matches[:5]:
            flag = "  ← NEW" if m["factory_id"] == fid else ""
            print(f"     #{m['rank']}  {m['factory_name']:<44} {m['score']['value']:>5.1f}/100{flag}")
        mine_m = next((m for m in matches if m["factory_id"] == fid), None)
        if mine_m:
            print(f"     → {CAPACITY['name']} ranks #{mine_m['rank']} of {len(matches)}: {' · '.join(mine_m['reasons'][:3])}")
    print("\nDone. Everything above is fictional demo data.")


if __name__ == "__main__":
    asyncio.run(main())
