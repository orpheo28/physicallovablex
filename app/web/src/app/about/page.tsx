import Link from "next/link";
import { Legend } from "@/components/Legend";
import { HeroSpecimen } from "@/components/HeroSpecimen";
import { STAGES, type Layer } from "@/lib/meta";

// Copy: ../gtm/landing_copy.md (W-GTM). Do not add claims.
const FACTS = [
  {
    text: "More than 75% of Kickstarter projects deliver late, and about 9% never deliver.",
    sources: [
      { name: "Mollick, SSRN 2014", url: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2088298" },
      { name: "SSRN 2015", url: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2699251" },
    ],
  },
  {
    text: "In 30 late campaigns we coded by hand, 18 of 24 documented causes were engineering or redesign, components or certification, not factory access.",
    note: "Small, hand-picked sample, not a statistic.",
    sources: [{ name: "internal GTM research (gtm-harness)", url: null }],
  },
  {
    text: "“As a newcomer to the industry, we didn't speak [the manufacturer's] language.”",
    note: "Halliday's COO, on the first smart glasses.",
    sources: [{ name: "Engadget, 21/07/2026", url: "https://www.engadget.com/2216393/halliday-g2-smart-glasses/" }],
  },
];

const LAYERS: { layer: Layer; title: string; body: string }[] = [
  { layer: "Lovable", title: "Design to decision", body: "Design, CAD, spec, investment, and where to produce. From one sentence to a buildable product and its cost." },
  { layer: "Core", title: "The Factory Pack", body: "DFM checks measured on the CAD, component risk and certification map, packed into a spec any factory can quote." },
  { layer: "Alibaba", title: "Factory network", body: "A curated factory network reached through the production MCP: capacity, MOQ, certifications, current load, quotes." },
  { layer: "Infra", title: "Getting it made", body: "Negotiation, tooling and samples, quality control, logistics and duties, financing." },
  { layer: "Brand", title: "Brand", body: "Name, packaging, landing copy, Shopify and Amazon listing drafts." },
];

const PACK = [
  "Product summary and target markets",
  "Structured spec: dimensions, materials, finishes, tolerances",
  "CAD (STEP) and drawings",
  "BOM with component risk and alternatives",
  "DFM alerts and resolutions",
  "Certification checklist by market",
  "Target quantities and cost estimate",
  "Questions for the factory (EN + CN)",
  "Assumption register",
];

const W = "mx-auto max-w-[1320px] px-6 lg:px-10";

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="max-w-[24ch] text-xl font-semibold tracking-[-0.02em] text-balance">{children}</h2>;
}

function CTA({ href, title, sub, primary }: { href: string; title: string; sub: string; primary?: boolean }) {
  return (
    <Link
      href={href}
      className={`group flex flex-col gap-2 rounded-md border p-5 transition-colors duration-150 ${
        primary ? "border-accent bg-accent text-ink hover:border-[#ff6a26] hover:bg-[#ff6a26]" : "border-line-2 bg-surface hover:border-ink-4"
      }`}
    >
      <span className="flex items-center justify-between text-md font-semibold tracking-[-0.01em]">
        {title}
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden>
          <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span className={`text-base ${primary ? "text-ink/75" : "text-ink-2"}`}>{sub}</span>
    </Link>
  );
}

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className={`${W} grid gap-x-16 gap-y-12 pb-24 pt-16 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:pt-20`}>
        <div className="flex flex-col">
          <h1 className="max-w-[14ch] text-[clamp(44px,5.4vw,64px)] font-semibold leading-[1.02] tracking-[-0.035em]">
            From idea to 1,000 units shipped.
          </h1>
          <p className="mt-7 max-w-[56ch] text-md text-ink-2">
            Hardware doesn&apos;t ship late because of design or because of the factory. It ships late because nobody translates the idea
            into what the factory can build. We do that translation, and hand you a Factory Pack any factory can quote.
          </p>
          <div className="mt-10 grid max-w-[640px] gap-3 sm:grid-cols-2">
            <CTA
              primary
              href="/?mode=idea"
              title="I have an idea"
              sub="Describe it in a sentence. Get the product, its cost and a factory shortlist in about a minute (measured on 10 test prompts)."
            />
            <CTA href="/?mode=prototype" title="I have a prototype" sub="Paste your BOM. We check what will slow your first production run." />
          </div>
          <p className="mt-4 flex items-center gap-2 text-sm text-ink-2">
            <span className="h-1.5 w-1.5 rounded-full bg-fictional" aria-hidden />
            Demo with simulated factories. Every number shows its source or its assumption.
          </p>
        </div>
        <HeroSpecimen />
      </section>

      {/* Problem */}
      <section className="border-t border-line bg-surface">
        <div className={`${W} py-20`}>
          <H2>Most launches slip between &ldquo;the prototype works&rdquo; and &ldquo;the factory ships good units.&rdquo;</H2>
          <div className="mt-12 grid border-t border-line md:grid-cols-3">
            {FACTS.map((f, i) => (
              <figure key={i} className={`flex flex-col py-6 md:pr-8 ${i > 0 ? "border-t border-line md:border-l md:border-t-0 md:pl-8" : ""}`}>
                <blockquote className="text-md font-medium leading-[26px] text-ink">{f.text}</blockquote>
                {f.note && <p className="mt-3 text-base text-ink-2">{f.note}</p>}
                <figcaption className="mt-auto pt-6 text-sm text-ink-3">
                  Source:{" "}
                  {f.sources.map((s, j) => (
                    <span key={j}>
                      {j > 0 && ", "}
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noreferrer" className="underline decoration-line-2 underline-offset-4 transition-colors hover:text-ink hover:decoration-ink">
                          {s.name}
                        </a>
                      ) : (
                        s.name
                      )}
                    </span>
                  ))}
                </figcaption>
              </figure>
            ))}
          </div>
          <p className="mt-8 text-md text-ink">Design tools and sourcing tools already exist. The gap is the translation between them.</p>
        </div>
      </section>

      {/* The Factory Pack */}
      <section className="border-t border-line">
        <div className={`${W} grid gap-12 py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]`}>
          <div>
            <H2>The Factory Pack: what a factory needs to quote.</H2>
            <p className="mt-5 max-w-[46ch] text-md text-ink-2">
              One document, nine sections. Negotiation starts from it, quality control checks against it, logistics uses its landed cost.
            </p>
          </div>
          <ol className="border-t border-ink">
            {PACK.map((x, i) => (
              <li key={x} className="grid grid-cols-[48px_1fr] items-baseline border-b border-line py-3 text-md">
                <span className="font-mono text-sm text-ink-3">§{i + 1}</span>
                {x}
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Layers */}
      <section className="border-t border-line bg-surface">
        <div className={`${W} py-20`}>
          <H2>Three layers — Lovable, Alibaba, Infra — around one core.</H2>
          <div className="mt-12 grid border-t border-line md:grid-cols-5">
            {LAYERS.map((l, i) => (
              <div key={l.layer} className={`relative py-6 md:pr-6 ${i > 0 ? "border-t border-line md:border-l md:border-t-0 md:pl-6" : ""}`}>
                {l.layer === "Core" && <span className="absolute -top-px left-0 right-0 h-[2px] bg-accent" aria-hidden />}
                <p className={`micro ${l.layer === "Core" ? "!text-accent-ink" : ""}`}>{l.layer}</p>
                <p className="mt-3 text-md font-medium">{l.title}</p>
                <p className="mt-2 text-base text-ink-2">{l.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Flow */}
      <section className="border-t border-line">
        <div className={`${W} py-20`}>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <H2>From brief to brand, in 13 stages.</H2>
            <p className="text-md font-medium">Export it all as one Launch Dossier (PDF).</p>
          </div>
          <ol className="mt-12 grid gap-x-12 border-t border-line md:grid-cols-2 md:[grid-auto-flow:column] md:[grid-template-rows:repeat(7,auto)]">
            {STAGES.map((s) => (
              <li key={s.n} className="grid grid-cols-[40px_1fr_auto] items-baseline gap-3 border-b border-line py-3.5">
                <span className="font-mono text-sm text-ink-3">{String(s.n).padStart(2, "0")}</span>
                <span className="text-base">
                  <span className="font-medium text-ink">{s.title}</span> <span className="text-ink-2">— {s.line}</span>
                </span>
                <span className={`text-2xs font-medium uppercase tracking-[0.08em] ${s.layer === "Core" ? "text-accent-ink" : "text-ink-3"}`}>{s.layer}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Trust */}
      <section className="border-t border-line bg-surface">
        <div className={`${W} py-20`}>
          <H2>You will always know what is real.</H2>
          <p className="mt-4 text-md text-ink-2">Every number on screen carries one of four labels. Hover any number to see its source or its assumption.</p>
          <div className="mt-10">
            <Legend detailed />
          </div>
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <p className="border-l-2 border-ink py-1 pl-5 text-base">
              <span className="font-medium">Real:</span> <span className="text-ink-2">brief, design, CAD, spec, measured checks, certification map, component prices, cost engine, production plan, brand kit.</span>
            </p>
            <p className="border-l-2 border-fictional py-1 pl-5 text-base">
              <span className="font-medium">Simulated:</span> <span className="text-ink-2">the factories, their capacity, quotes and replies, freight rates.</span>
            </p>
          </div>
        </div>
      </section>

      {/* Next */}
      <section className="border-t border-line">
        <div className={`${W} grid gap-10 py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]`}>
          <H2>Next: a real factory network.</H2>
          <div>
            <p className="max-w-[64ch] text-md text-ink-2">
              Today the factories in this demo are fictional. Next, we onboard real factories by hand, one at a time, through a production
              MCP: an open interface where a factory lists its processes, MOQ, certifications, lead times and current load, and any agent
              (ours, Claude, ChatGPT or your own) can ask for capacity and request a quote. Every Factory Pack is reviewed by a human
              engineer before a real factory sees it.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <span className="text-base font-medium">Want to be among the first founders or factories?</span>
              <button disabled className="h-8 cursor-not-allowed rounded border border-line-2 px-3 text-sm text-ink-3">
                Coming after the demo
              </button>
              <Link href="/factories" className="text-sm text-ink-2 underline decoration-line-2 underline-offset-4 transition-colors hover:text-ink hover:decoration-ink">
                See the (fictional) factory portal
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
