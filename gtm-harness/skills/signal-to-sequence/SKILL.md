---
name: signal-to-sequence
description: Turn one detected signal on one account into a short outreach sequence (email, then LinkedIn, then one follow-up) that quotes that exact signal and asks for a discovery conversation.
---

# Signal to sequence

**Input:** an account plus one signal. The signal needs its URL, its date and the exact wording from the source. The best input is the output of `account-research`.
**Output:** three messages (email, LinkedIn note, follow-up), ready to send and personalised on the signal.

## Rules (from `03_DISCOVERY/messages.md`)
- Never mention Hexa or the project name.
- Introduce yourself honestly as someone studying hardware sourcing.
- Sell nothing, promise nothing, take no money. Ask for a conversation, never a sale.
- **Cite the precise signal:** the update number or date, and the problem in the founder's own words. A generic "saw you're delayed" is not allowed.
- Use only a high-confidence signal. If the page was not reopened, do not quote it.
- Never mention the backers' anger. Talk about the problem, not the blame.

## Reference messages
These are the two templates in `outputs/campaign-01-discovery/brief.md`. `03_DISCOVERY/messages.md` has "Templates: (à rédiger)", so these are the first version.

**Email (day 0)**
```
Subject: {Product}: your {update #n | month} update

Hi {First name},

I read your {date} update on {Product}: "{exact quote of the signal}".

I'm studying why hardware launches slip between prototype and mass
production, and I'm talking to founders who have been through it.
I'm not selling anything.

Could you give me 20 minutes this week? I'd like to understand what
actually took longer than planned: the design, the components,
certification or the factory. Happy to share what I hear from the
other founders in return.

Orphéo Hellandsjo
```

**LinkedIn connection note (day 1, 300 characters max)**
```
Hi {First name}, I read your {month} update on {Product} ({signal, 8 words max}).
I'm studying why hardware launches slip after the prototype. Could I ask you
20 min about what really caused it? Not selling anything, and happy to share
what other founders tell me.
```

**Follow-up (day 3, reply in the email thread)**
```
{First name}, one precise question if 20 minutes is too much: was
{their problem} something you could have seen coming at the prototype
stage, or did it only appear at the factory?
```

## Steps
1. Pick the strongest signal for the account. See the weights in `context/signals.md`.
2. Fill `{exact quote}` with a sentence copied from the source, not a paraphrase.
3. Adapt the "design, components, certification or factory" line so it names the account's bucket first.
4. Circular Ring 2 is a Paris startup: send its messages in French (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).
5. Log what was sent in `outputs/accounts.csv`, in the `message_envoye` and `reponse` columns, and in the tracking table in `brief.md`.

## Worked example (AIVELA Ring Pro, score 4)
Signal source: ["About half of the units made in that batch passed final checks… the rest were held back due to component quality issues"](https://gadgetsandwearables.com/2026/02/12/aivela-ring-pro-shipping/) (12/02/2026).
> Subject: AIVELA Ring Pro: your February update
> Hi Donghao, I read your February update on the Ring Pro: "about half of the units made in that batch passed final checks… the rest were held back due to component quality issues." I'm studying why hardware launches slip… Could you give me 20 minutes? I'd like to understand how that component was chosen and qualified, and what actually took longer than planned.
