"""Scripted BUYER agent over the production MCP (HTTP): search capacity → read the profile → request a quote.

    uv run python -m factory_mcp.demo.buyer_agent [--url http://localhost:8000/mcp] [--token …]

Brief: LSR overmolding + PCBA, 2,000 units, ISO 9001, before 2026-12-15. All data is fictional demo data.
"""

from __future__ import annotations

import asyncio
from datetime import date

from factory_mcp.demo._client import Transcript, connect, parse_args

QTY, CERTS, DEADLINE = 2000, ["ISO 9001"], date(2026, 12, 15)
BRIEF = "silicone fitness band with PCBA — LSR overmolding + PCBA, 2,000 units, ISO 9001, before 2026-12-15"
# one search per process the product needs (search_capacity ranks for a single process)
SEARCHES = [("injection_molding", "LSR silicone"), ("pcba", "FR-4")]


def show_matches(matches: list[dict], limit: int = 5) -> None:
    for m in matches[:limit]:
        print(f"     #{m['rank']}  {m['factory_name']:<44} {m['score']['value']:>5.1f}/100   ({m['factory_id']})")
        print(f"          {' · '.join(m['reasons'][:3])}")


async def main() -> None:
    args = parse_args(__doc__.splitlines()[0])
    say = Transcript("buyer agent")
    async with connect(args.url, args.token) as client:
        tools = [t.name for t in (await client.list_tools()).tools]
        say.say(f"Connected to {args.url} — {len(tools)} tools: {', '.join(tools)}")
        say.say(f"Brief: {BRIEF}")

        totals: dict[str, float] = {}
        seen: dict[str, int] = {}
        names: dict[str, str] = {}
        for process, material in SEARCHES:
            say.say(f"Searching capacity: {process} / {material}")
            matches = await say.call(client, "search_capacity", process=process, material=material, quantity=QTY,
                                     certifications_required=CERTS, deadline=DEADLINE.isoformat())
            show_matches(matches)
            for m in matches:
                totals[m["factory_id"]] = totals.get(m["factory_id"], 0) + m["score"]["value"]
                seen[m["factory_id"]] = seen.get(m["factory_id"], 0) + 1
                names[m["factory_id"]] = m["factory_name"]
        # prefer one supplier that covers every process (one RFQ), ranked by summed score; else the best partial fit
        pool = [f for f in totals if seen[f] == len(SEARCHES)] or list(totals)
        best = max(pool, key=lambda f: (totals[f], f))
        say.say(f"Best fit covering both processes: {names[best]} ({totals[best]:.1f} pts summed)")

        profile = await say.call(client, "get_factory_profile", factory_id=best)
        cap = profile["capacity"]
        print(f"     {profile['name']} — {profile['region']}")
        print(f"     processes: {', '.join(cap['processes'])}")
        print(f"     MOQ {cap['moq']:,} · lead time {cap['lead_time_days']} d · {cap['monthly_capacity']:,} units/month "
              f"· {cap['current_load_pct']:.0f}% loaded · certs: {', '.join(cap['certifications']) or 'none'}")
        for note in profile.get("audit_notes", [])[:2]:
            print(f"     audit: {note}")

        say.say("Requesting a quote for 500 / 2,000 / 10,000 units")
        out = await say.call(client, "request_quote", factory_id=best, factory_pack_id="fp_fitness_band_demo",
                             quantities=[500, 2000, 10000], product_name="Silicone fitness band with PCBA")
        print(f"     RFQ sent: {out['rfq_id']} — it now shows in {profile['name']}'s portal")
    print("\nDone. Everything above is fictional demo data.")


if __name__ == "__main__":
    asyncio.run(main())
