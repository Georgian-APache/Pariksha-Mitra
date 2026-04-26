"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

export function SubjectRadar({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).map(([subject, value]) => ({
    subject,
    mastery: Math.round(value * 100),
  }));
  if (rows.length === 0) return <div className="text-sm text-muted-foreground">No data yet.</div>;
  return (
    <div className="w-full h-[260px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={rows}>
          <PolarGrid stroke="oklch(1 0 0 / 0.12)" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "oklch(0.85 0 0)", fontSize: 12 }} />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: "oklch(0.6 0 0)", fontSize: 10 }}
            stroke="oklch(1 0 0 / 0.05)"
          />
          <Radar
            name="Mastery"
            dataKey="mastery"
            stroke="oklch(0.78 0.16 200)"
            fill="oklch(0.62 0.2 280 / 0.4)"
          />
          <Tooltip
            contentStyle={{
              background: "oklch(0.18 0.02 270)",
              border: "1px solid oklch(1 0 0 / 0.08)",
              borderRadius: 8,
            }}
            labelStyle={{ color: "oklch(0.95 0 0)" }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
