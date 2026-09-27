"use client";

import { Suspense } from "react";
import { StartProject } from "@/components/StartProject";
import { GalleryStrip } from "@/components/Gallery";
import { Skeleton } from "@/components/ui";

/** Start screen, one screen: the centered prompt, then the showcase of what others made. */
export default function Home() {
  return (
    <div className="mx-auto flex h-full min-h-0 max-w-[1200px] flex-col justify-center gap-[clamp(28px,6vh,64px)] px-10 pb-6 pt-2">
      <Suspense fallback={<Skeleton className="mx-auto h-72 w-full max-w-[760px]" />}>
        <StartProject />
      </Suspense>
      <GalleryStrip />
    </div>
  );
}
