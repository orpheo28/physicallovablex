import Link from "next/link";
import type { Label } from "@/types/contracts";
import { LABEL_DOT, LABEL_HELP, LABEL_TEXT } from "@/lib/meta";

const ORDER: Label[] = ["measured", "sourced", "estimate", "fictional"];

/** Bottom status bar: the one trust-label legend and the demo disclaimer, on every screen. */
export function StatusBar() {
  return (
    <footer data-chrome className="flex h-7 items-center gap-4 overflow-hidden bg-paper px-5 text-2xs text-ink-3">
      {ORDER.map((l) => (
        <span key={l} data-tip={LABEL_HELP[l]} data-tip-label={l} className="inline-flex shrink-0 cursor-help items-center gap-1.5 text-ink-2">
          <span className={`tdot ${LABEL_DOT[l]}`} aria-hidden />
          {LABEL_TEXT[l]}
        </span>
      ))}
      <span className="hidden truncate xl:inline">Hover a dot for its source or assumption.</span>
      <span className="ml-auto truncate">Case-study demo. All factories, quotes and freight rates are fictional demo data. No real personal data is stored.</span>
      <Link href="/about" className="shrink-0 text-ink-2 transition-colors hover:text-ink">
        About
      </Link>
    </footer>
  );
}
