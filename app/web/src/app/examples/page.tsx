"use client";

import { GalleryCard } from "@/components/Gallery";
import { ScrollArea } from "@/components/ScrollArea";
import { BtnLink, ErrorBox, Skeleton } from "@/components/ui";
import { useShowcase } from "@/lib/showcase";

/** All showcase projects (GET /examples; until it exists, the pre-computed demo projects). */
export default function ExamplesPage() {
  const { cards, error, fromApi } = useShowcase();
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)]">
      <div className="flex items-end justify-between gap-4 px-10 pb-4 pt-6">
        <div>
          <h1 className="title text-[28px] leading-[34px]">Examples</h1>
          <p className="mt-2 max-w-[72ch] text-md text-ink-2">
            Products designed with PhysicalLovableX, from one sentence to a factory-ready pack. Open one to see its Studio conversation or its overview.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {cards && (
            <span className="text-sm text-ink-3">
              <span className="font-mono text-ink">{cards.length}</span> {fromApi ? "showcase projects" : "pre-computed examples"}
            </span>
          )}
          <BtnLink href="/" variant="primary">
            Make your own
          </BtnLink>
        </div>
      </div>
      <ScrollArea className="h-full px-10 pb-10 pt-6" label="Examples">
        {error && <ErrorBox message={`Could not load the examples: ${error}`} />}
        <div className="grid grid-cols-3 gap-5 min-[1440px]:grid-cols-4">
          {!cards && !error && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[300px] w-full" />)}
          {cards?.map((c) => (
            <GalleryCard key={c.projectId} c={c} tall />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
