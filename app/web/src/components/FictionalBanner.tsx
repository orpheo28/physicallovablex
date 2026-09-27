export function FictionalBanner() {
  return (
    <div className="bg-fictional-soft">
      <p className="mx-auto flex max-w-[1320px] items-center gap-2.5 px-6 py-2 text-sm text-fictional-ink lg:px-10">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-fictional" aria-hidden />
        <strong className="font-semibold">Fictional — demo data.</strong>
        These factories, their capacity, quotes and performance are simulated. No real factory is named.
      </p>
    </div>
  );
}
