# Content plan — 4 weeks of founder-led teardowns

**Nothing is published this week.** Orphéo posts by hand, later, after the PMF-independent checks below. Every fact in a post carries a link; if a fact cannot be reopened, it is cut (`gtm-harness/CLAUDE.md`: no source, not written).

## The playbook (Waniwani audit, transposed)
Waniwani publishes audits of its prospects' ChatGPT apps, scored out of 25 with the method published. That is named outbound dressed as media, aimed at accounts that already moved (`../../02_RECHERCHE/hexa_wtf_waniwani.md`). We transpose it to **public teardowns of late hardware launches**: public, sourced, useful.
- **Public:** only what the company itself published (campaign updates, press, product pages).
- **Sourced:** every claim links to its source; estimates are ranges labelled `[E]` with the method (`skills/pvp-teardown`).
- **Useful:** each teardown ends with a checklist a founder can apply to their own product before the prototype is frozen.

## Rules of engagement (ethics + credibility)
1. **Never blame.** Talk about the problem, not the founder; never mention backers' anger (`signal-to-sequence` rule).
2. **Right of reply.** Before publishing a teardown about a live company, send them the draft 3 working days ahead and offer to correct errors. Log in `outputs/accounts.csv`. Accounts we already contacted for discovery are not used until the call is done.
3. **No pitch in the post.** One line at the end: "I'm studying why launches slip; DMs open." No product name, no Hexa (same rule as discovery).
4. **Estimates are ranges**, never a single point (pvp-teardown rule).
5. **Prefer closed stories:** launches already documented in press (Halliday, HOVERAir AQUA) before small founders still in the middle of a crisis.
6. **No automation:** no scheduler, no bot replies (`GTM_STACK.md`, the rule).
7. **Reddit:** read each subreddit's rules first (⚠️ not verified here); no links to us; give value first; disclose we are researching.

## Weekly rhythm (30 min/day, Hypothesis)
| Day | Action |
|---|---|
| Mon | Pick the teardown, run `pvp-teardown` + `account-research`, verify every source |
| Tue | Send right-of-reply draft (live companies) |
| Wed | Write the three formats |
| Thu | X thread + LinkedIn post |
| Fri | Reddit post + answer every comment for 48h |
**Metric (leading, Hypothesis):** inbound DMs from founders, replies naming their own blocker, subscribers. Not impressions. **Decision rule:** if after 4 weeks no post produced a founder reply, change the format (shorter, more numbers) before changing the topic.

## Four weeks — topics only

| Week | Teardown | Thesis bucket | X + LinkedIn angle | Reddit community (⚠️ verify rules) | Sources to reopen |
|---|---|---|---|---|---|
| 1 | **Halliday G1 → G2: "we didn't speak the manufacturer's language"** | Factory translation | What a factory needs in a spec that a founder new to the industry does not know to include | r/Kickstarter or r/hardware, as a question: "what did you learn the hard way about talking to your factory?" | [Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/) (21/07/2026) |
| 2 | **Pilet: a redesign mid-campaign** | Engineering / components | How a component change (Raspberry Pi CM5) ripples into enclosure, firmware and certification; checklist before choosing a compute module | r/raspberry_pi or r/embedded (component-choice angle) | [c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/) |
| 3 | **HOVERAir AQUA and the FCC ban: certification is a launch risk, not a paperwork step** | Certification | Certification checklist by market; what to ask your factory about radio modules and test labs | r/drones or r/hardware | [DroneXL](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/) (28/05/2026) |
| 4 | **AIVELA Ring Pro: half the units passed final checks** + KONKR RAM price "nearly tripled" | Components / QC | Component qualification and price-drift: what to lock in a quote and what an AQL plan catches | r/startups or r/Entrepreneur ("what would you check before paying for a production run") | [Gadgets & Wearables](https://gadgetsandwearables.com/2026/02/12/aivela-ring-pro-shipping/) (12/02/2026), [GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html) |

Backup topics: Wordrunner (public date passed, still "pre-order"), The Minimal Phone (⚠️ medium confidence), the "delay causes" table as a data post (the 30-account coding, with its small-sample caveat, `gtm-harness/CLAUDE.md`).

---

## Example post 1 — X thread (Week 2, Pilet)
**Verify against the source before posting: the quotes and dates below come from `gtm-harness/CLAUDE.md` and `context/signals.md`; reopen the article and add the exact wording.**

> 1/ Pilet's Kickstarter update #20 announced a redesign around the Raspberry Pi CM5. A public, well-told story about how one component decision moves everything around it. A thread on what to check before you pick your compute module. 🧵
>
> 2/ Why this matters: a compute module isn't a part, it's a constraint. It sets the board size, the thermals, the power budget, the connectors and, if it has radios, your certification path.
>
> 3/ The pattern in public updates: redesigns after a campaign are the most common documented cause of slips. In a small hand-coded sample of 30 late campaigns, 18 of 24 documented causes were engineering/redesign, components or certification, not factory access. (Small, non-random sample. Method on request.)
>
> 4/ Checklist before choosing the compute module:
> • Is it in stock, and from how many sources? (lead time, EOL status)
> • What does it do to the enclosure: height, heat, ports?
> • Does it bring wireless? Then which certifications, in which markets?
> • Can your factory place it in SMT, or is it a hand-assembly step?
>
> 5/ None of this is Pilet's fault. It's what happens when a first product meets a real supply chain. Source: c33tech, "How not to Pilet a Kickstarter": https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/
>
> 6/ I'm studying why hardware launches slip after a successful campaign: design, components, certification or the factory. If you've been through it, my DMs are open. Not selling anything.

## Example post 2 — LinkedIn (Week 1, Halliday)
> **"As a newcomer to the industry, we didn't speak [the manufacturer's] language."**
>
> That's Halliday's COO, on why the first smart glasses had "many mistakes" ([Engadget, 21 July 2026](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)).
>
> It's the most honest sentence I've read about hardware this year, because it names the gap most founders never name. Not design. Not finding a factory. The translation between the two.
>
> What "speaking the factory's language" means in practice, as a checklist:
> 1. A drawing with tolerances, not a render.
> 2. A BOM with alternates for every single-source part.
> 3. Materials and finishes named, not described.
> 4. Target quantities per tier, because price and process change with volume.
> 5. The markets you'll sell in, because certification decides the components.
> 6. Questions to the factory written before the first quote, not after the first sample fails.
>
> Halliday is now preparing the G2 with this lesson. The founders who learn it before the first run save months.
>
> I'm studying why launches slip between prototype and production. If you've been there, I'd like to hear what actually took longer. DMs open.

## Example post 3 — Reddit (Week 3, certification)
**Subreddit:** r/hardware or r/drones (⚠️ read the rules; if self-promotion or research posts are restricted, post as a discussion question only). **Title:** *What certification questions do you wish you'd asked before your first hardware run? (HOVERAir AQUA's US refund story as a case)*

> I'm researching why hardware launches slip after the prototype works, and one case keeps coming up: HOVERAir AQUA. According to DroneXL (28 May 2026), its US backers were refunded after an FCC ban on the product's category ([source](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/)). I'm not commenting on the company; the story is public and it's a useful case.
>
> What I take from it: certification is not a form at the end. It decides the radio module, the antenna layout, sometimes the whole product's viability in a market, and it's often decided by rules that change after your campaign is funded.
>
> A rough checklist I'd build from public sources (please correct me, I'm not an engineer):
> - Which markets will you sell in, and which rules apply to each (FCC for the US; CE/UKCA for EU/UK)?
> - Is any part of your product on a restricted list, or made by a supplier that might be?
> - Do you have a test lab lined up *before* tooling, and what's their queue?
> - What's the plan and cost if certification fails after the first run?
>
> Two questions for people who've shipped hardware: what did you get wrong first, and what would you check on day one now? I'm collecting answers to write a proper checklist, and I'll share the result here.

## Funnel mapping and distribution loop (added 26/09)
Every post must do one of three jobs:
- **Attention (top):** building-in-public stories — what we learn talking to hardware founders, the thesis evolving (v1 → v2).
- **Trust (middle):** the founder's real concerns — why launches slip after a successful campaign, DFM before tooling, certification surprises, "speaking the factory's language". Public, sourced teardowns live here.
- **Evaluation (bottom):** the product at work — a Factory Pack before/after, measured DFM alerts on a real prototype (with permission), time and cost saved on a named run.

**Distribution:** each week, connect with ~100 funded or pre-launch hardware founders (signals: live or recently funded Kickstarter/Indiegogo campaigns, "delivery update" posts).
**Engager signal (warm outbound):** each week, export ICP-matching likers, commenters and profile viewers → score with `skills/icp-scoring` → add to the discovery tracker as a warm signal (source: "engaged with post <date>").
**Feedback loop:** track format, hook, topic and media per post; keep what brings ICP engagers, drop the rest.
Gate: starts in Phase 2 (see GTM_STACK.md); nothing published before Hexa validates the name and the public story.
