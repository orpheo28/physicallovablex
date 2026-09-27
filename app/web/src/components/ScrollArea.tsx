"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, type ReactNode } from "react";

/**
 * A designated scroll region (the page itself never scrolls). Thin brand scrollbar; the top / bottom
 * edge fades only when there is more content in that direction, so the fade reads as "more here".
 */
export const ScrollArea = forwardRef<HTMLDivElement, { children: ReactNode; className?: string; id?: string; as?: "div" | "main" | "section"; label?: string }>(
  function ScrollArea({ children, className = "", id, as = "div", label }, ref) {
    const el = useRef<HTMLDivElement>(null);
    useImperativeHandle(ref, () => el.current as HTMLDivElement);

    const update = useCallback(() => {
      const n = el.current;
      if (!n) return;
      const top = Math.min(20, n.scrollTop);
      const bottom = Math.min(20, n.scrollHeight - n.clientHeight - n.scrollTop);
      n.style.setProperty("--fade-top", `${Math.max(0, top)}px`);
      n.style.setProperty("--fade-bottom", `${Math.max(0, bottom)}px`);
    }, []);

    useEffect(() => {
      const n = el.current;
      if (!n) return;
      update();
      const ro = new ResizeObserver(update);
      ro.observe(n);
      for (const c of Array.from(n.children)) ro.observe(c);
      const mo = new MutationObserver(update);
      mo.observe(n, { childList: true, subtree: true });
      return () => {
        ro.disconnect();
        mo.disconnect();
      };
    }, [update]);

    const Tag = as;
    return (
      <Tag ref={el} id={id} onScroll={update} className={`scroll-y min-h-0 ${className}`} data-scroll aria-label={label}>
        {children}
      </Tag>
    );
  },
);
