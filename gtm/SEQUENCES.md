# Sequences — written, not executed

**Nothing here is sent by an agent.** Orphéo reviews and sends by hand, one account at a time, after checking the placeholders. Every `{...}` is filled from `outputs/accounts.csv` and the call notes; if a value is missing, the sentence is deleted, not invented.

**Working name.** `{PRODUCT}` is a placeholder. The rule "never mention Hexa or the project name" (`gtm-harness/CLAUDE.md`) holds for cold discovery messages. Sequences 1-3 come **after** a call or a warm reply, and each names the offer plainly; use the working name only if Hexa agrees. Otherwise say "a hardware production project I'm helping scope".

**Promises.** The offer is a free, human-reviewed Factory Pack. We promise no price, no delivery date, no guarantee. Positioning ("committed landed price") stays a hypothesis until lighthouse (`context/positioning.md`).

---

## Sequence 1 — Lighthouse offer to founders who took a discovery call
**Trigger:** call held and coded in `verbatims.md`. **Goal (PRD A3):** ≥3 packs accepted; if <3 in lighthouse, rethink the wedge. **Segment:** A only; do not send to established manufacturers (anti-ICP).
**Cadence:** D+0 (within 24h of the call) → D+4 → D+9 → stop. Three touches, no more.

**Email 1 — D+0, thank-you + offer**
```
Subject: Thanks — and a Factory Pack for {PRODUCT_NAME}

Hi {First name},

Thank you for the time on {day}. What stayed with me: "{one short quote from the call, with their OK}".

You said {their blocker, in their words} took the longest. Here is something concrete, no charge:
I'd like to prepare a Factory Pack for {PRODUCT_NAME}. It is a spec package a factory can quote without back-and-forth:
structured spec, BOM with component risks and alternatives, DFM alerts, a certification checklist for {their markets},
estimated landed cost at {their volumes}, and the questions to ask your factory in English and Chinese.

An engineer reviews it before you see it. It costs nothing and asks for nothing.
I'd need: your BOM or component list, the CAD or drawings if you have them, and your target markets and volumes.
Your files stay with us and nobody else sees them; tell me if you want an NDA first.

If useful I can send it within {N} working days of receiving the files. (Fill N only after the engineer confirms.)

Orphéo
```
**Email 2 — D+4, one useful thing, no chasing**
```
Subject: Re: Thanks — and a Factory Pack for {PRODUCT_NAME}

{First name}, one thing from the other founders I've spoken to that may help regardless of what you decide:
{one anonymised, sourced observation, e.g. "a redesign after the campaign was the most common cause we found in public updates"}.
The offer stands: no charge, reviewed by an engineer. If a full pack is too much, I can start with just the certification checklist for {markets}.
```
**Email 3 — D+9, close the loop**
```
Subject: Closing the loop

{First name}, I'll stop here so I don't clutter your inbox. If timing changes (a new run, a new product, a certification question),
the offer is open. And if the pack isn't useful, I'd value one line on why; that helps me more than a yes.
```
**Decision rule:** yes → log in `accounts.csv`, book a 30-min scoping call, start the Factory Pack. No reply after email 3 → tag "no", do not re-contact for 30 days. A "no" with a reason goes to `verbatims.md` (feeds A2/A3: is it a painkiller?).

---

## Sequence 2 — Factory onboarding to the production MCP
**Trigger:** a shortlisted factory (from the supply side of PRD §4.4) with a public contact. **Goal (PRD A4):** onboard 3 factories by hand; capacity profiles completed; measure RFQ-to-quote time. **Do not use fictional demo factory names in any message.**
**Cadence:** D+0 email → D+5 follow-up → D+12 last note.

### EN
```
Subject: Qualified, complete RFQs for {factory} — free to try

Hello {Name},

I'm working on a service that prepares complete production packages for hardware founders (CAD, BOM, tolerances, certification needs, target quantities) so that a factory can quote without a long exchange of emails.

We are looking for a small number of factories to test with, starting with {process} for {product category}.
What you would do: fill in a short capacity profile (processes, materials, MOQ, certifications, lead time, current load). What you get: RFQs that are already complete, with the founder's real quantities and target timeline.
No fee, no exclusivity. You decide whether to quote each RFQ.

Could we have a 15-minute call, or would you prefer I send the profile form first?

Orphéo Hellandsjo
```
### 中文 (short) — ⚠️ machine-drafted, to be reviewed by a native speaker before sending
```
主题：为{工厂名}提供完整、合格的报价请求（免费试用）

{联系人}您好，

我们正在为硬件创业者准备完整的生产资料包（CAD、BOM、公差、认证要求、目标数量），让工厂无需反复沟通即可报价。
目前我们在寻找少量工厂试用，首先是{工艺}，产品类别为{品类}。

您只需填写一份简短的产能资料（工艺、材料、起订量、认证、交期、当前负荷）。您将收到信息完整的询价，含创业者的真实数量和目标时间。
免费，无排他条款，是否报价由您决定。

方便安排15分钟电话吗？或者我先发资料表给您？

Orphéo Hellandsjo
```
**Follow-up (D+5, EN, 40 words):** "Hello {Name}, following up on my note about complete RFQs. I can send a one-page capacity form (about 10 minutes to fill) instead of a call. Would that be easier?"
**Decision rule:** ≥1 profile in 5 sent → continue; 0 in 10 → drop the MCP-first pitch and use an RFQ-only flow, capacity inferred from quotes (PRD A4 fallback).

---

## Sequence 3 — Partner channel (crowdfunding platforms / product-design agencies)
**Why:** the Applied Intuition lesson, "distribution defines the business": go through actors who already hold the founder's trust (`lecons_inputs.md`). The Waniwani model uses partner channels too (`../../02_RECHERCHE/hexa_wtf_waniwani.md`).
**Two targets, two angles.** Do not contact a platform's creators directly through the platform; only through the partner's public business contact.
**Cadence:** D+0 → D+6 → D+14, then stop.

**3a. Crowdfunding platform / campaign-services partner** (e.g. Kickstarter, Indiegogo, BackerKit, PledgeBox, per `accounts.csv`; ⚠️ verify each has a public partnerships contact)
```
Subject: Helping funded hardware creators reach production

Hi {Name},

Most creators on {platform} who fund a hardware product then face the same gap: turning a working prototype into something a factory can quote and build.
Public data suggests the causes are mostly engineering, components and certification rather than factory access (small hand-coded sample of 30 campaigns; happy to share the method).

I'm testing a free, human-reviewed "Factory Pack" that closes that gap. Would you be open to a 20-minute call to hear whether it would be useful for your creators, and how you'd want to be involved (a resource page, an intro, or nothing at all)?

Orphéo Hellandsjo
```
**3b. Product-design agency / freelance industrial designer**
```
Subject: After the CAD is done — a Factory Pack for your clients

Hi {Name},

Design agencies often hand over a beautiful design and then watch the client struggle with DFM, components and certification. We prepare a Factory Pack (spec, BOM with risks, DFM alerts, certification checklist, cost estimate, EN + CN questions for the factory), reviewed by an engineer.

I'd like to try it free on one of your finished projects, with your client's permission. If it helps them, you can offer it as the next step. Open to a 20-minute call?

Orphéo Hellandsjo
```
**Follow-up (D+6, 35 words):** "Hi {Name}, quick nudge on my note. I can send a sample Factory Pack for a demo product so you see what your creators/clients would receive. Would that be useful?"
**Decision rule:** ≥2 conversations → 1 referral in 30 days → keep as a channel. Zero referrals after 5 conversations → drop, focus on direct signal-led outreach. Any revenue share is **not** offered now.
