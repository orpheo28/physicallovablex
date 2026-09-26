# GTM stack by phase

**Status: designed, not executed.** Only Phase 1 tools marked "on now" run this week, and they run by hand. Sources: `../PRD.md` §17-18, `../../02_RECHERCHE/lecons_inputs.md`, `../gtm-harness/`. Costs are **orders of magnitude (Hypothesis)**, not quotes; check vendor pricing before buying.

## The rule
**No automated sending and no paid acquisition before product-market fit.**
- Elena Verna (Lovable): paid in year one is a deadly trap; her benchmark is under 10% paid and payback under 3 months (`lecons_inputs.md`). Hardware has long cycles, so our budget for paid is **0**.
- NanoCorp and Polsia send cold emails and buy ads before any demand is proven; a third-party review says nobody checks the thing deserves to exist (`../../02_RECHERCHE/concurrents.md` §1). We do the opposite.
- **PMF gate (Hypothesis, to confirm after lighthouse):** at least 3 production runs started and a first published on-time and defect rate (PRD §18, Phase 1 exit). Until the gate is passed, every message is written by an agent, **reviewed and sent by Orphéo by hand**.
- Automation is allowed for reading, scoring and drafting. It is never allowed for sending, posting or spending.

---

## Phase 1 — Lighthouse (0-90 days): manual + harness
Goal: 10 founders, 3 factories onboarded by hand, ≥3 production runs (PRD §18).

| Tool | Role | Switched on | Trigger metric | Cost order |
|---|---|---|---|---|
| `gtm-harness/` skills (icp-scoring, account-research, signal-to-sequence, pvp-teardown) | Find and score accounts, draft the message, produce the teardown offered after a call | **On now** | Runs on every new account | Model tokens only, ~$ tens/month |
| `accounts.csv` / `03_DISCOVERY/comptes.csv` + tracking table in `brief.md` | CRM. One row per account, one row per signal type | **On now** | 30 messages sent this week | $0 |
| Email + LinkedIn, sent by hand | Discovery outreach, then lighthouse offer | **On now** | ≥20% replies, ≥3 calls (brief targets) | $0; LinkedIn Premium optional, ~$ tens/month |
| Call notes → `verbatims.md`, coded by root cause | Test thesis v2 (design / components / certification / factory / logistics) | **On now** | ≥2 in 3 calls name design, components or certification | $0 |
| Human engineer review of every Factory Pack | The "last 10%" (PRD principle 4) | When the first lighthouse founder accepts a pack | 100% of tier-2 packs signed | Engineer time: the real cost, freelance ~$ hundreds per pack (Hypothesis) |
| Factory onboarding by hand (WeChat / email + the MCP schema) | Create capacity data that does not exist publicly (`E_usines.md`) | After the first pack is ready to quote | 3 capacity profiles completed; RFQ-to-quote time | $0 + travel/time |
| Public teardowns (see `CONTENT_PLAN.md`) | Authority, inbound from the ICP | Week 3 of Phase 1, only after the first calls | 1 teardown/week; replies from named founders | $0 |

## Phase 2 — Land grab (3-9 months): content + community + sequences
Goal: Factory Packs exported per week, pack → RFQ conversion (PRD §18). Free tier is the marketing budget (Verna).

| Tool | Role | Switched on | Trigger metric | Cost order |
|---|---|---|---|---|
| Self-serve MVP, tier 1 public | Wow moment → Factory Pack export | Lighthouse gate passed | Packs exported/week (north-star input) | Model + hosting, ~$ hundreds/month at low volume (Hypothesis); free-tier cost is the CAC |
| Founder-led content (X, LinkedIn, one Reddit community/week) | Teardowns of late launches | Already started manually in Phase 1 | Weekly teardowns published; inbound DMs | $0 |
| Email sequences (`SEQUENCES.md` 1-3) via a plain sequencer, **human approval per batch** | Lighthouse offer, factory onboarding, partner channel | ≥10 discovery calls logged and coded | Reply rate ≥20%; call → pack acceptance | Sequencer ~$ tens/month |
| Community: makerspace / design-school "build a product" weekends (Verna: sponsored hackathons) | Wow-moment events, top of funnel | After tier 1 is public | Packs exported at events | Venue + snacks, ~$ hundreds/event |
| Product analytics (PostHog is already connected in this environment) | Funnel: prompt → wow screen → export | Tier 1 public | Activation = Factory Pack exported | Free tier |
| Open Factory Pack format + MCP spec on GitHub | "Open-source tool + demo video + waitlist" genesis (`lecons_inputs.md`) | Once ≥3 packs were accepted by real factories | Stars, third-party agents querying the MCP | $0 |
| Partner channel (crowdfunding platforms, product-design agencies) | Distribution through actors who already hold the founder's trust (Applied Intuition lesson) | Sequence 3 replies exist | ≥2 partner conversations → 1 referral | $0 (rev-share is a Phase 3 question) |

## Phase 3 — Scale (9-24 months): infra
Goal: factories self-register capacity; third-party agents query the MCP (PRD §18).

| Tool | Role | Switched on | Trigger metric | Cost order |
|---|---|---|---|---|
| Public MCP + factory self-serve registration | Supply-side network effect ("Waniwani for industrial capacity") | Capacity profiles from ≥10 factories hand-verified | Factories registering without us; agent queries/week | Engineering time |
| Published on-time / defect dashboard | Trust asset nobody else has (`positioning.md`) | From run 1, updated per run | On-time rate, defect rate, rejected lots | $0 |
| Partner integrations (financing, logistics) | Tier 3 take rate | Reorder volume is measurable | Reorders per founder | Partner-dependent |
| Outbound hire (one SDR/AE, **not before PMF**) | Founding Sales rule: founders sell first, hire once the motion repeats | Repeatable motion documented | Founder-led win rate stable | Salary |
| Paid acquisition | Only as an experiment, never the base | **Only after PMF and payback < 3 months** (Verna) | Payback < 3 months, paid < 10% of acquisition | Capped budget, set then |

---

## Phase 2 tools (not used this week)
Descriptions below are **as given in the brief and not verified by us** (⚠️ check each before any use). None is installed, none touches a real prospect.

| Tool | What it is (per brief) | Intended role | Gate before switching on | Rule |
|---|---|---|---|---|
| **Hermes Agent** (Nous Research, MIT license, self-hosted) | Open-source agent, run on our own machine | **Signal watcher:** reads the public pages listed in `context/signals.md` (campaign `/posts`, product pages still saying "Pre-order", job posts) and writes a candidate list + quotes to a file | Phase 1 done: the signal weights in `signals.md` were validated against ≥10 coded calls | **Read-only.** It proposes accounts, it never contacts them. Self-hosted so scraped data and founder names stay with us. Kickstarter and Reddit return 403: outputs stay "medium confidence" |
| **Grok Bot** (xAI, beta, autonomous agents) | Autonomous agents from xAI, beta | Drafting and triage on X (replies, reposts of teardowns) | **Only after PMF.** Beta status = unstable behaviour | **Human approval on every send.** No autonomous posting, replying or DMs. Never in a founder's mentions unprompted |
| **TypeSafe Jev** (typed-decision model) | Model that outputs typed decisions (fixed categories rather than free text) | High-volume classification: tag each update/comment with the root-cause bucket (design / components / certification / factory / logistics / none) and each reply as interested / not now / no | ≥500 signals to classify (below that, Claude + a spreadsheet is enough) and a hand-labelled test set of ≥100 to measure accuracy | Classification only. Its output feeds scoring; it never triggers a send |

Why wait: we have 30 accounts and a hand-coded sample of 30 (`gtm-harness/CLAUDE.md`). A tool built for volume solves a problem we do not have yet, and an autonomous sender before PMF is exactly what the rule forbids.
