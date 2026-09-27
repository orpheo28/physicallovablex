# Limits

PhysicalLovableX is a concept-to-manufacturing-package tool. Read this before relying on any output.

## What it is not

- **Concept-level CAD.** Geometry is good enough to see, measure, cost and brief a factory. It is not tooling-ready or production-ready. About 80% of the translation from idea to a factory-ready package is automated; humans and real factories cover the last 20%.
- **Not a prototype.** A working prototype takes weeks, not minutes. The prototype path estimates the cost and time.
- **Not a marketplace.** No real payments, no real logistics booking, no real order placement.

## Fictional data

- The 11 factories, the integrator, the 3 installers, their capacity, quotes, negotiation replies, past performance, carrier freight quotes and transit days are **fictional demo data**, labeled on screen, in the PDF and in every API record. Factory names end with "(fictional)".
- Negotiation is a real agent loop over the MCP tools, but every reply is simulated.
- In Make it, the quote is **auto-approved** so the flow can complete. That decision stands in for a human. Review the selected factory before any real order.

## Estimates

Mechanical parts, assembly, tooling ranges, certification costs and lead times, freight derivation, financing ranges and build-strategy figures (MOQ, entry cost, lead time) are **Estimates**. The HTS classification is a precedent from CBP rulings, not a binding classification; confirm with a customs broker.

Component prices and stock come from a dated snapshot (LCSC / JLCPCB) and can be out of date. Check stock and price before ordering, and surface low-stock parts as risks.

## What humans must sign off

- Any real order, contract or payment.
- Design freeze, tooling release and samples approval.
- Certification testing and the declarations for each market.
- HTS classification and duties with a broker.
- Firmware: the skeleton is generated and **not compiled or tested**.
- Safety-critical categories (child furniture, mains appliances, batteries): standards references guide the work, they do not certify it.

## Availability behaviour

If the AI service is unavailable (key, credit cap, rate limit or timeout), a step serves a cached example labeled "Cached example". A failed refine changes nothing. Public demo deployments may be read-only (no live AI runs) and rate limited per IP.

## Coming soon

- **Text-to-PCB:** today the electronics architecture stops at power tree and netlist-level connections; layout is a human or future text-to-PCB step.
- **Real factory onboarding:** the network is a demo today; the registration flow exists, real audited factories do not.
