"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function TrendChart({
  history,
}: {
  history: { timestamp: string; readiness: number }[];
}) {
  const data = history.map((h) => ({
    t: new Date(h.timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    readiness: Math.round(h.readiness),
  }));
  if (data.length === 0) {
    return <div className="text-sm text-muted-foreground">Trend will populate as you study.</div>;
  }
  return (
    <div className="w-full h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: -20 }}>
          <defs>
            <linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.62 0.2 280)" stopOpacity={0.6} />
              <stop offset="100%" stopColor="oklch(0.62 0.2 280)" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="oklch(1 0 0 / 0.06)" />
          <XAxis dataKey="t" tick={{ fill: "oklch(0.65 0 0)", fontSize: 10 }} stroke="oklch(1 0 0 / 0.1)" />
          <YAxis domain={[0, 100]} tick={{ fill: "oklch(0.65 0 0)", fontSize: 10 }} stroke="oklch(1 0 0 / 0.1)" />
          <Tooltip
            contentStyle={{
              background: "oklch(0.18 0.02 270)",
              border: "1px solid oklch(1 0 0 / 0.08)",
              borderRadius: 8,
            }}
          />
          <Area
            type="monotone"
            dataKey="readiness"
            stroke="oklch(0.78 0.16 200)"
            strokeWidth={2}
            fill="url(#trend-fill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
