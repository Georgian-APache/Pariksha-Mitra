"use client";

import { CalendarDays, Brain, BookOpen, Repeat, Target } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { WeeklyPlan } from "@/lib/types";

const ACTIVITY_META: Record<
  string,
  { icon: typeof Brain; label: string; tone: "default" | "accent" | "warning" | "success" }
> = {
  learn: { icon: BookOpen, label: "Learn", tone: "default" },
  quiz: { icon: Brain, label: "Quiz", tone: "accent" },
  drill: { icon: Target, label: "Drill", tone: "warning" },
  review: { icon: Repeat, label: "Review", tone: "success" },
};

export function PlanStrip({ plan }: { plan: WeeklyPlan }) {
  if (!plan?.days?.length) {
    return <div className="text-sm text-muted-foreground">No plan yet - run the diagnostic first.</div>;
  }
  return (
    <div className="space-y-3">
      {plan.rationale && (
        <div className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground/80">Why this plan:</span> {plan.rationale}
        </div>
      )}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
        {plan.days.map((d) => (
          <div
            key={d.date}
            className="flex-shrink-0 w-56 rounded-lg border border-border bg-card/40 p-3 space-y-2"
          >
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-1 font-medium">
                <CalendarDays className="size-3.5 text-muted-foreground" />
                {new Date(d.date + "T00:00").toLocaleDateString(undefined, {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                })}
              </div>
              <span className="text-xs text-muted-foreground">{d.total_minutes}m</span>
            </div>
            <div className="space-y-1.5">
              {d.blocks.map((b, i) => {
                const meta = ACTIVITY_META[b.activity] ?? ACTIVITY_META.learn;
                const Icon = meta.icon;
                return (
                  <div
                    key={i}
                    className="rounded-md border border-border/60 bg-background/40 p-2 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant={meta.tone} className="gap-1 text-[10px]">
                        <Icon className="size-3" />
                        {meta.label}
                      </Badge>
                      <span className="text-muted-foreground">{b.minutes}m</span>
                    </div>
                    <div className="font-medium truncate" title={b.concept_id}>
                      {b.concept_id}
                    </div>
                    <div className="text-muted-foreground">{b.subject}</div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
