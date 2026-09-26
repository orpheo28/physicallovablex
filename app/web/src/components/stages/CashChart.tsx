"use client";

import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CashPoint } from "@/types/contracts";

const INK = "#111111";
const ACCENT = "#FF4F00";
const INK3 = "#8A8883";
const LINE = "#E6E4DF";
const MONO = "var(--font-num), ui-monospace, monospace";

export default function CashChart({ points }: { points: CashPoint[] }) {
  const data = points.map((p) => ({
    date: p.date,
    short: new Date(p.date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }),
    description: p.description,
    cash_out: p.cash_out.value,
    cumulative: p.cumulative.value,
  }));
  const usd = (v: number) => `$${Math.round(v).toLocaleString("en-US")}`;
  const k = (v: number) => (Math.abs(v) >= 1000 ? `$${Math.round(v / 1000)}k` : `$${v}`);
  return (
    <div>
      <div className="mb-3 flex items-center gap-5 text-sm text-ink-2">
        <span className="flex items-center gap-2">
          <span className="h-[2px] w-4 bg-ink" aria-hidden /> Cumulative cash out
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-[1px] bg-accent" aria-hidden /> Cash out at milestone
        </span>
      </div>
      <ResponsiveContainer width="100%" height={300} initialDimension={{ width: 800, height: 300 }}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={LINE} vertical={false} />
          <XAxis
            dataKey="short"
            tick={{ fontSize: 11, fill: INK3, fontFamily: MONO }}
            tickLine={false}
            axisLine={{ stroke: LINE }}
            tickMargin={8}
          />
          <YAxis tickFormatter={k} tick={{ fontSize: 11, fill: INK3, fontFamily: MONO }} tickLine={false} axisLine={false} width={52} />
          <Tooltip
            cursor={{ fill: "rgba(17,17,17,0.04)" }}
            contentStyle={{
              background: "#fff",
              border: `1px solid ${LINE}`,
              borderRadius: 4,
              boxShadow: "none",
              fontSize: 12,
              padding: "8px 10px",
            }}
            labelStyle={{ color: INK, fontWeight: 500, marginBottom: 4 }}
            itemStyle={{ fontFamily: MONO, padding: 0 }}
            formatter={(v, name) => [usd(Number(v)), name === "cumulative" ? "Cumulative (Estimate)" : "Cash out (Estimate)"]}
            labelFormatter={(_, p) => (p && p[0] ? `${p[0].payload.date} · ${p[0].payload.description}` : "")}
          />
          <Bar dataKey="cash_out" fill={ACCENT} barSize={14} radius={[1, 1, 0, 0]} />
          <Line type="stepAfter" dataKey="cumulative" stroke={INK} strokeWidth={1.5} dot={{ r: 2.5, fill: INK, strokeWidth: 0 }} activeDot={{ r: 4 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
