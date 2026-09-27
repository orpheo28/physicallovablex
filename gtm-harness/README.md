# PhysicalLovableX: GTM harness

The go-to-market harness for PhysicalLovableX, an idea Hexa WTF is scoping. It finds hardware founders whose launches are slipping, learns from them why, and keeps what it learns in files Claude Code reads at the start of every session. Start with `CLAUDE.md` (2-minute read).

## Structure
```
gtm-harness/
├── README.md                          this file
├── CLAUDE.md                          product, ECP vs ICP, top signals, positioning, current priorities, thesis v2, rules
├── context/                           what we believe (sourced or labelled Hypothesis)
│   ├── profile.md                     company, product, real vs simulated, deal profile (hypothesis), no references yet
│   ├── icp.md                         ECP vs ICP, tiers, qualification questions, anti-ICP, beachhead scoring, evolution log
│   ├── signals.md                     6 signals: detection, points, decay, combination bonus, hook, performance table
│   ├── positioning.md                 one-liner, value pillars with proof, messaging matrix per face, guardrails
│   ├── competitors.md                 battlecards incl. DIY / "contact in Shenzhen", Accio, Monce; win/loss log
│   └── personas/
│       ├── hardware-founder.md        user = buyer (observed + hypotheses, objections, hooks)
│       ├── factory-owner.md           supply side (mostly hypothesis)
│       └── ecosystem-partner.md       intermediaries: engineering studios, backer tools, agents, QC, 3PL (hypothesis)
├── skills/                            repeatable procedures
│   ├── icp-scoring/SKILL.md
│   ├── account-research/SKILL.md
│   ├── signal-to-sequence/SKILL.md
│   ├── pvp-teardown/SKILL.md
│   ├── call-debrief/SKILL.md          new 27/09
│   └── weekly-update/SKILL.md         new 27/09
├── workflows/                         decision trees
│   ├── signal-routing.md              fire → dedupe/suppress → score → research → human approves → human sends → log
│   ├── campaign-build.md              audience → brief → sequence → human QA gate → human send → review 48 h / 7 d
│   └── enrichment.md                  public sources only, 403 handling, fields required before drafting
├── playbooks/                         what to do when X happens
│   ├── new-signal-response.md
│   ├── founder-replied.md             book, prep, run the 5 questions, debrief
│   └── factory-intro.md               factories via intermediaries, never cold
└── outputs/                           what the harness produced
    ├── accounts.csv                   45 scored accounts (mirror of 03_DISCOVERY/comptes.csv before batch 3; source now has 55)
    ├── RUN_LOG.md                     one line per skill run + naming rule + index of pre-27/09 files
    ├── weekly-log.md                  one line per weekly update or harness change
    ├── research/                      account cards (the-minimal-phone, pilet, wordrunner)
    ├── pvp/                           teardowns (halliday, wordrunner)
    └── campaign-01-discovery/         brief.md, tracking.md (36 drafts, ~32 sendable, warm track counts)
```
New output files are named `YYYY-MM-DD-[type]-[name].md`; files created before 27/09 keep their names and are indexed in `outputs/RUN_LOG.md`. Context file names were kept (not renamed to `icp-definition.md`, `signal-library.md`, `competitor-radar.md`) because the deck cites them by path.

## Running each skill
From this folder in Claude Code, ask for the skill by name ("Read `skills/<name>/SKILL.md` and run it on …").
| Skill | Ask | Returns |
|---|---|---|
| **icp-scoring** | "Run icp-scoring on `<list>`" | Urgency 1-5, priority points with decay, bucket, tier, sourced justification; `outputs/YYYY-MM-DD-scoring-<list>.md` |
| **account-research** | "Run account-research on `<account>`" | Card: sourced problem, one root-cause bucket, angle, channel type; `outputs/research/YYYY-MM-DD-research-<account>.md` |
| **signal-to-sequence** | "Run signal-to-sequence on `<account>` with signal `<URL + quote>`" | Email, LinkedIn note, follow-up as drafts for a human; contacts stay in `03_DISCOVERY/` |
| **pvp-teardown** | "Run pvp-teardown on `<product URL>`" | Landed-cost range and risks, `[S]` vs `[E]` apart; offered after a call only |
| **call-debrief** | "Run call-debrief on the `<account>` entry in verbatims.md" | One root-cause tag; updates signal performance, persona objections, win/loss, ICP log; no transcript stored |
| **weekly-update** | "Run weekly-update" | Stale sections, drafted updates (applied after you confirm), one row in `outputs/weekly-log.md` |

## Maintenance cadence (2-person pre-seed)
| When | What | Who | Time |
|---|---|---|---|
| Same hour as each send or reply | `03_DISCOVERY/envoi/SUIVI.md` first, then `tracking.md` | O | 2 min |
| Within 30 min of each call | `verbatims.md`, then `skills/call-debrief` | O | 15 min |
| Each send batch | Per-signal counts in `context/signals.md` | O (agent drafts) | 5 min |
| Weekly (Sunday) | `skills/weekly-update`: priorities, decay re-check, mirrors, persona objections | O (agent drafts) | 15 min |
| After 5 coded calls or 30 days | ICP evolution log entry; re-score if the ICP changes | O | 30 min |
| After any call naming an alternative | `context/competitors.md` win/loss log | O | 10 min |
| End of each campaign | Keep / change / kill; campaign results in its `tracking.md` | O | 30 min |
| When the product changes | `context/profile.md`, `positioning.md` (truth: `PRODUIT.md`) | O | 15 min |

O = Orphéo. The second person (engineer contractor, W2) is a Hypothesis (deck slide 9) and owns no harness file yet.

## How this harness ran on 26-28/09
1. **Before 26/09, signals and scoring:** 45 accounts scored 1-5 with the `icp-scoring` rubric (`outputs/accounts.csv`).
2. **26/09, research:** `account-research` on the top 3 drafts (Minimal Phone, Pilet, Wordrunner) → `outputs/research/`.
3. **26/09, teardowns:** `pvp-teardown` on Halliday and Wordrunner → `outputs/pvp/` (ranges, low confidence).
4. **26/09, messages:** 23 drafts in `03_DISCOVERY/envoi/A_ENVOYER.md`, follow-ups in `RELANCE.md`.
5. **27/09, more accounts:** batch 2 (#24-#26) and batch 3 (#27-#36, 10 new accounts from Crowd Supply and founder blogs) → **36 drafts, ~32 sendable**; `03_DISCOVERY/comptes.csv` now 55 rows.
6. **27/09, warm track:** 10 network messages drafted in `RESEAU.md` (target 2 calls before Mon 11:30).
7. **27/09, decisions:** consumer electronics first; beachhead scoring; ECP ≠ ICP; Monce added to competitors (`context/icp.md` evolution log).
8. **27/09, harness upgrade:** this structure (see `outputs/weekly-log.md`).
9. **27-28/09 (planned):** a human sends, logs in `SUIVI.md`, mirrors into `tracking.md`; each call coded with `call-debrief`. **0 sends logged on 27/09.**
10. **Restitution (planned):** tags vs success criteria in `brief.md`; update `icp.md` and `CLAUDE.md`.

## What is not in this repo (on purpose)
- **No sync scripts, no API keys, no sending tool.** Nothing automated sends, schedules or publishes; every message is sent by a human. This keeps founders' data out of third-party tools and keeps the human QA gate real.
- **No contact lists.** Contact points live in `03_DISCOVERY/` (outside the harness); warm-network names never enter it. `outputs/accounts.csv` (legacy mirror, 45 rows) keeps only public founder names and public page URLs; the 7 email addresses were removed on 27/09 (originals stay in `03_DISCOVERY/`), so it passes the export check.
- **No raw transcripts, no founder BOMs or files, no pricing terms.** Calls are synthesised by `call-debrief`.

## Credits
Structure adapted from Maja Voje, ["The GTM repository for Claude Code"](https://knowledge.gtmstrategist.com/p/the-gtm-repository-for-claude-code) (GTM Strategist), and from Karl Rafidimanana's [gtm-starter-kit](https://github.com/KarlRaf/gtm-starter-kit) (The Revenue Architects), MIT License. Layers (context / skills / workflows / playbooks / outputs), file roles, short section headings, the signal decay and combination idea, the "delete the ask" value test and the output naming rule come from those sources. No text was copied beyond short headings; all content here is ours and sourced to this case.
