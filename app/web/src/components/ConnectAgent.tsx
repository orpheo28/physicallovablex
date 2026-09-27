"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { apiSchema } from "@/lib/autofill";

const TOOLS = ["search_capacity", "get_factory_profile", "register_capacity", "request_quote", "submit_quote", "counter_offer", "accept_quote"];

/** "Connect your agent": the production MCP over HTTP (W22). Hidden when this API does not expose /mcp. */
export function ConnectAgent() {
  const [on, setOn] = useState(false);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let live = true;
    Promise.all([
      apiSchema().then((j) => Object.keys(j?.paths ?? {}).some((p) => p === "/mcp" || p.startsWith("/mcp/"))),
      fetch("/mcp-status", { cache: "no-store" })
        .then((r) => r.json() as Promise<{ exists?: boolean }>)
        .then((j) => !!j.exists)
        .catch(() => false),
    ]).then(([a, b]) => live && setOn(a || b));
    return () => {
      live = false;
    };
  }, []);
  if (!on) return null;
  const url = `${API_URL.replace(/\/$/, "")}/mcp`;
  // Local API: no token and a -local server name (MCP_DEMO); deployed: your token in the header.
  const local = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(url);
  const cmd = local
    ? `claude mcp add --transport http physicallovablex-local ${url}`
    : `claude mcp add --transport http physicallovablex ${url} --header "Authorization: Bearer <your token>"`;
  async function copy() {
    try {
      await navigator.clipboard.writeText(cmd);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <section aria-labelledby="mcp-h" className="relative mb-8 grid gap-x-10 gap-y-5 rounded-lg bg-surface p-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
      <div className="min-w-0">
        <p className="micro">Production MCP</p>
        <h2 id="mcp-h" className="mt-0.5 text-lg font-semibold tracking-[-0.015em]">
          Connect your agent
        </h2>
        <p className="mt-1 text-base text-ink-2">Any AI agent can search capacity, request quotes and register capacity.</p>
        {/* The command sits in one dark block with its copy action: the one thing to take away from this card. */}
        <div className="mt-4 overflow-hidden rounded-md bg-ink text-white">
          <div className="flex items-center justify-between gap-3 px-4 pt-2.5">
            <span className="text-2xs text-white/55">
              Claude Code · endpoint <span className="font-mono text-white/80">{url}</span>
            </span>
            <button onClick={copy} className="press shrink-0 rounded-sm px-2 py-0.5 text-2xs font-medium text-white/80 hover:bg-white/10 hover:text-white" aria-live="polite">
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <code className="block whitespace-pre-wrap break-all px-4 pb-3 pt-1.5 font-mono text-[12.5px] leading-5 text-white">{cmd}</code>
        </div>
        <p className="mt-2 text-2xs text-ink-3">
          {local ? "Local API: no token needed." : "Replace <your token> with the token you were given."} The factory network behind it is fictional demo data.
        </p>
      </div>
      <div className="min-w-0">
        <p className="text-sm text-ink-3">Tools</p>
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {TOOLS.map((t) => (
            <li key={t} className="rounded-full bg-paper px-3 py-1 font-mono text-[12px] text-ink-2">
              {t}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
