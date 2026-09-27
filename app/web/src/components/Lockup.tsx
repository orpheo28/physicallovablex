/**
 * Brand lockup: Hexa logo · hairline divider · PhysicalLovableX wordmark · quiet "Case study" tag.
 * Spec in docs/BRAND.md §6. The favicon stays neutral (app/icon.svg), never the Hexa mark.
 */
export function Lockup({ size = "md", tag = true }: { size?: "md" | "lg"; tag?: boolean }) {
  const lg = size === "lg";
  return (
    <span className={`inline-flex items-center ${lg ? "gap-3.5" : "gap-3"}`}>
      {/* A plain <img>: a small static asset (public/brand/) needs no optimizer round-trip, and it must load on /login before sign-in. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/hexa-logo.webp" alt="Hexa" width={lg ? 72 : 61} height={lg ? 26 : 22} className={`${lg ? "h-[26px]" : "h-[22px]"} w-auto shrink-0`} />
      <span className={`w-px shrink-0 bg-line-2 ${lg ? "h-5" : "h-4"}`} aria-hidden />
      <span className={`whitespace-nowrap font-semibold tracking-[-0.01em] text-ink ${lg ? "text-md" : "text-base"}`}>PhysicalLovableX</span>
      {tag && (
        <span className="inline-flex h-5 shrink-0 items-center rounded-full bg-paper-2 px-2 text-2xs font-medium text-ink-2">
          Case study
        </span>
      )}
    </span>
  );
}
