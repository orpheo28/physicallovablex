# Overview

PhysicalLovableX turns a sentence into a physical product you can see, refine and prepare for manufacturing.

In software, the AI writes code. In hardware, **CAD is code**: the AI writes [build123d](https://github.com/gumyr/build123d) code, runs it in a sandbox, measures the result and repairs its own errors. You see the product in 3D with its unit cost and a factory shortlist, change it by prompting, and press **Make it** to run the rest of the path to a launch package.

## The loop

| Step | What happens |
|---|---|
| **Describe** | One sentence: "A Whoop competitor, screenless, 5-day battery." |
| **See** | The product in 3D, its unit cost at three volumes, and the top factories, on one screen. |
| **Refine** | Prompt changes ("add SpO2 and skin-temperature sensing", "make it pink", "thinner, 8 mm pod", "target retail $149"). Each prompt creates a restorable **version** with a diff: CAD, BOM with real LCSC parts, costs, measured DFM, certifications, shortlist. |
| **Make it** | One action runs factories (via the production MCP), agent negotiation, tooling, QC, shipping and duties, cash plan and brand, and produces the **Launch Dossier** (EN + CN). |

Recorded examples open instantly at no AI cost from the showcase gallery (`GET /examples`). The Studio is the primary interface. The 13 stages behind it are the detailed view of the same project (see [Concepts](/docs/concepts)).

## Recorded timings

Measured live over several runs. Not guarantees, and they vary with load and the product:

- First version: 18-24 s.
- Colour or feature refine: 4-7 s.
- Geometry refine (the AI edits its CAD program): 11-24 s.
- Make it, 13 steps to the Launch Dossier: 54-88 s live; instant, $0 on a recorded showcase.

## What is real, what is demo

Every number in the product carries one label: **Measured**, **Sourced**, **Estimate** or **Fictional — demo data**.

- **Real:** AI-written CAD and its measurements, measured DFM checks, physics checks, LCSC prices and stock (dated snapshot), HTS lines from CBP CROSS rulings, the Drewry freight index, PVGIS solar yield.
- **Fictional and labeled:** the 11 factories, 1 integrator and 3 installers, their capacity, quotes and negotiation replies, carrier freight quotes and transit days.
- **Categories:** wearables, furniture, home robot, vacuum, irrigation, rooftop solar, surfboard, lighting, tracker, drone, hair dryer, camera, smartphone. The build strategy (full design, module assembly or ODM customization) is chosen per category.
- **Generated, not verified:** firmware skeletons are labeled "not compiled or tested".

Details in [Limits](/docs/limits).

## Connect your agent

The production MCP is served over Streamable HTTP at `/mcp`. Use your own token; never paste it into a shared config.

**Claude Code** (from the project's demo guide):

```bash
claude mcp add --transport http physicallovablex-production \
  https://physicallovablex-production.up.railway.app/mcp \
  --header "Authorization: Bearer $MCP_TOKEN"
```

**Claude Desktop** (stdio bridge via `mcp-remote`, needs Node). Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "physicallovablex-production": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://physicallovablex-production.up.railway.app/mcp",
               "--header", "Authorization:${AUTH_HEADER}"],
      "env": { "AUTH_HEADER": "Bearer PASTE_MCP_TOKEN_HERE" }
    }
  }
}
```

**Cursor** and **Codex** (untested): both are MCP clients that accept a Streamable HTTP server URL with a custom header. Point them at `https://physicallovablex-production.up.railway.app/mcp` with header `Authorization: Bearer <token>`. We have not tested these two clients; if your client only speaks stdio, use the `mcp-remote` bridge shown above.

**Any MCP client, no setup** — check the endpoint with curl:

```bash
curl -s https://physicallovablex-production.up.railway.app/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Full reference: [Production MCP](/docs/production-mcp).

## Where next

- [Quickstart](/docs/quickstart) — first product in the app and through the API.
- [Concepts](/docs/concepts) — Factory Pack, versions, the 13 steps, honesty labels, build strategies.
- [Studio API](/docs/studio-api) — every route.
- [Production MCP](/docs/production-mcp) — the 7 tools.
- [Engineering](/docs/engineering) — category packs, build strategy, physics checks, firmware, prototype path.
- [Limits](/docs/limits) — honest scope.
- [agents.md](/agents.md) — instructions for AI agents.
