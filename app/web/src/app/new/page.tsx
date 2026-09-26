"use client";

import { Suspense } from "react";
import { StartProject } from "@/components/StartProject";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-12 lg:px-10">
      <Suspense fallback={<div className="text-sm text-ink-3">Loading…</div>}>
        <StartProject title="New project" />
      </Suspense>
    </div>
  );
}
