"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import type { MoodEntry } from "@/lib/types";

type Props = { history: MoodEntry[] };

export function MoodChart({ history }: Props) {
  const data = history.slice(-14).map((e) => ({
    date: e.timestamp.slice(0, 10).slice(5), // MM-DD
    score: e.score,
  }));

  if (!data.length) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No mood data yet — check in daily to see your trend.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0 0 / 0.1)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[1, 10]} ticks={[1, 3, 5, 7, 10]} tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "oklch(0.15 0.01 280)", border: "none", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "oklch(0.9 0 0)" }}
        />
        <Line
          type="monotone" dataKey="score" stroke="oklch(0.65 0.15 290)"
          strokeWidth={2} dot={{ r: 3, fill: "oklch(0.65 0.15 290)" }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
