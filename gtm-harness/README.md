# PhysicalLovableX: GTM harness

This repo is the go-to-market harness for PhysicalLovableX, an idea Hexa WTF is scoping. Its purpose is to find hardware founders whose launches are slipping and to learn from them why.
- `context/` holds the hypotheses: ICP, signals, positioning, competitors and persona. Every claim is sourced.
- `skills/` holds four repeatable procedures that an agent (Claude Code) or a person can run on any new account.
- `outputs/` holds the scored account base and the live campaigns.

Rules and thesis v2 are in `CLAUDE.md`. Read it first.

## Structure
```
gtm-harness/
├── README.md                      this file
├── CLAUDE.md                      project, thesis v2, repo rules, how files connect
├── context/
│   ├── icp.md                     segments A and B, anti-ICP, open question (hypothesis)
│   ├── signals.md                 signal | how to detect | weight
│   ├── positioning.md             committed landed price and quality guarantee
│   ├── competitors.md             who does what, funding, weak point, our difference
│   └── personas/hardware-founder.md
├── skills/
│   ├── icp-scoring/SKILL.md
│   ├── account-research/SKILL.md
│   ├── signal-to-sequence/SKILL.md
│   └── pvp-teardown/SKILL.md
└── outputs/
    ├── accounts.csv               45 scored accounts (copy of 03_DISCOVERY/comptes.csv)
    ├── RUN_LOG.md                 one line per skill run
    ├── pvp/                       teardowns (halliday.md, wordrunner.md)
    ├── research/                  account cards (the-minimal-phone.md, pilet.md, wordrunner.md)
    └── campaign-01-discovery/
        ├── brief.md               objective, questions, success criteria, links to the files below
        └── tracking.md            mirror of 03_DISCOVERY/envoi/SUIVI.md with the signal table
```

## Running each skill
From this folder in Claude Code, ask for the skill by name.
- **icp-scoring:** "Run icp-scoring on `<list.csv>`" returns a 1-5 score and a sourced justification per account, in `accounts.csv` format.
- **account-research:** "Run account-research on `<account>`" returns a card with its precise, sourced production problem, the root-cause bucket and the angle of approach.
- **signal-to-sequence:** "Run signal-to-sequence on `<account>` with signal `<URL + quote>`" returns an email, a LinkedIn note and a follow-up that quote the signal.
- **pvp-teardown:** "Run pvp-teardown on `<product URL>`" returns the landed cost range and the risk points, with sourced `[S]` and estimated `[E]` lines kept apart.

## How this harness ran on 26-28/09
1. **Before 26/09, signals and scoring:** the 45 accounts in `outputs/accounts.csv` carry a 1-5 score from the `icp-scoring` rubric and the signals in `context/signals.md`. Not re-run on 26/09.
2. **26/09, research:** `skills/account-research` ran on the top 3 drafts (Minimal Phone, Pilet, Wordrunner); cards are in `outputs/research/`.
3. **26/09, teardowns:** `skills/pvp-teardown` ran on Halliday and Wordrunner; pages are in `outputs/pvp/`. Estimates are ranges with their method and low confidence.
4. **26/09, message:** 23 drafts, none sent, are in `03_DISCOVERY/envoi/A_ENVOYER.md`; follow-ups are in `RELANCE.md`.
5. **26/09, tracking:** `outputs/campaign-01-discovery/tracking.md` mirrors `SUIVI.md`. Nothing is sent yet, so all counts are 0.
6. **27-28/09 (planned):** a human sends the messages, logs each send in `SUIVI.md` and mirrors it into `tracking.md`.
7. **27-28/09 (planned):** each call is logged in `03_DISCOVERY/verbatims.md` with one root-cause tag.
8. **Restitution (planned):** the tags are compared with the success criteria in `brief.md`, then `context/icp.md` and `CLAUDE.md` are updated.
9. Every run is listed in `outputs/RUN_LOG.md` with what a human must still check.
10. Nothing in this harness sends anything; all outreach is a human action.

```
signals ──> scoring ──> research ──> message ──> tracking ──> verbatims ──> ICP update
signals.md  icp-scoring account-    signal-to-  tracking.md  verbatims.md  icp.md +
            accounts.csv research   sequence    (SUIVI.md)   (cause tag)   CLAUDE.md
                        pvp-teardown A_ENVOYER.md
```
