import type { Label } from "@/types/contracts";
import { LABEL_DOT, LABEL_HELP, LABEL_INK, LABEL_TEXT } from "@/lib/meta";

const ORDER: Label[] = ["measured", "sourced", "estimate", "fictional"];

function Chip({ l }: { l: Label }) {
  return (
    <span data-tip={LABEL_HELP[l]} data-tip-label={l} className={`inline-flex cursor-help items-center gap-1.5 text-sm font-medium ${LABEL_INK[l]}`}>
      <span className={`tdot ${LABEL_DOT[l]}`} aria-hidden />
      {LABEL_TEXT[l]}
    </span>
  );
}

export function Legend({ detailed }: { detailed?: boolean }) {
  if (detailed)
    return (
      <dl className="grid sm:grid-cols-2 lg:grid-cols-4">
        {ORDER.map((l, i) => (
          <div key={l} className={`flex flex-col gap-2 py-5 pr-6 ${i > 0 ? "lg:pl-6" : ""}`}>
            <dt>
              <Chip l={l} />
            </dt>
            <dd className="text-base text-ink-2">{LABEL_HELP[l]}</dd>
          </div>
        ))}
      </dl>
    );
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {ORDER.map((l) => (
        <Chip key={l} l={l} />
      ))}
      <span className="ml-1 text-ink-3">Hover a dot for its source or assumption.</span>
    </div>
  );
}
