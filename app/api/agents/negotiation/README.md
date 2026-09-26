# api/agents/negotiation/

**Owner: W5 — MCP + Negotiation.** Only this session edits this folder.

| Module | What |
|---|---|
| `matching.py` | `@stage_handler(7)`: one `search_capacity` query per process in the Factory Pack (process per part from stage 6, else `process_hint`; + assembly), part-weighted product ranking → shortlist of 5 with breakdown + reasons. `generated_by: "code"` |
| `rfq.py` | `@stage_handler(8)`: `request_quote` to the top 3 → 3 factory agents (`fast`) `submit_quote` anchored on stage-5 tiers × personality → negotiation agent (`main`) `counter_offer` (price, tooling, MOQ, lead time, 30/70), max 2 rounds → recommendation; CN lines via `cn`. No key → same flow with the scripted policy (`fallback: false`, `generated_by: "code"`). `{"approve": true, "quote_id"?}` → `accept_quote`, `user_approved`, `final_terms` (label fictional) |
| `provider.py` | `@provider("network")` → factory portal routes read the MCP store |
| `_policy.py` | Deterministic personalities, first quotes, counters, concessions, risk-adjusted pick; clamps LLM numbers |
| `_inputs.py` | Factory Pack / stage-5 anchors / reference quantity / queries |
| `_tests/` | `uv run pytest api/agents/negotiation` |

Stage 8 outputs read downstream: `final_terms` (W4 stage 9, W3 stage 11), `recommendation.quote_id`.
