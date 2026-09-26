"use client";

import { useEffect, useState } from "react";

/** Wall clock ticking every `ms` while `active` (for progress indicators). */
export function useNow(active: boolean, ms = 250) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [active, ms]);
  return now;
}
