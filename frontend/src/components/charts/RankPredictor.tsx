"use client";

import { TrendingUp } from "lucide-react";
import type { RankPrediction } from "@/lib/types";

export function RankPredictor({ prediction }: { prediction: RankPrediction | null }) {
  if (!prediction) {
    return (
      <div className="text-sm text-muted-foreground">
        Rank simulator activates once your exam date is set.
      </div>
    );
  }
  const p = prediction;
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <div className="text-3xl font-semibold">{p.expected_percentile.toFixed(1)}%ile</div>
        <div className="text-sm text-muted-foreground">expected on exam day</div>
      </div>
      <div className="text-xs text-muted-foreground">
        90% CI: {p.percentile_low.toFixed(1)} - {p.percentile_high.toFixed(1)} {" | "}
        {p.days_to_exam} days to go {" | "} Monte Carlo over {p.samples} trajectories
      </div>
      <div className="relative h-3 rounded-full bg-input overflow-hidden">
        <div
          className="absolute inset-y-0 bg-primary/40"
          style={{
            left: `${p.percentile_low}%`,
            width: `${Math.max(0, p.percentile_high - p.percentile_low)}%`,
          }}
        />
        <div
          className="absolute inset-y-0 w-1 bg-accent"
          style={{ left: `${p.expected_percentile}%` }}
        />
      </div>
      <div className="flex items-center gap-1 text-xs text-accent">
        <TrendingUp className="size-3" />
        Readiness: {p.expected_readiness.toFixed(1)} (band {p.readiness_low.toFixed(1)} - {p.readiness_high.toFixed(1)})
      </div>
    </div>
  );
}
