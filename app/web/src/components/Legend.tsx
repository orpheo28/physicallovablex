import type { Label } from "@/types/contracts";
import { LABEL_CLASS, LABEL_DOT, LABEL_HELP, LABEL_TEXT } from "@/lib/meta";

const ORDER: Label[] = ["measured", "sourced", "estimate", "fictional"];

function Chip({ l }: { l: Label }) {
  return (
    <span title={LABEL_HELP[l]} className={`inline-flex h-5 cursor-help items-center gap-1.5 rounded-full px-2 text-2xs font-medium ${LABEL_CLASS[l]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${LABEL_DOT[l]}`} aria-hidden />
      {LABEL_TEXT[l]}
    </span>
  );
}

export function Legend({ detailed }: { detailed?: boolean }) {
  if (detailed)
    return (
      <dl className="grid border-t border-line sm:grid-cols-2 lg:grid-cols-4">
        {ORDER.map((l, i) => (
          <div key={l} className={`flex flex-col gap-3 border-b border-line py-5 pr-6 lg:border-b-0 ${i > 0 ? "lg:border-l lg:pl-6" : ""}`}>
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
      <span className="ml-1 text-ink-3">Hover any number for its source or assumption.</span>
    </div>
  );
}
