"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  Brain,
  CalendarDays,
  Compass,
  HeartHandshake,
  Microscope,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { API_URL } from "@/lib/api";
import type { AgentStep } from "@/lib/types";

const ICONS: Record<AgentStep["agent"], typeof Brain> = {
  orchestrator: Compass,
  planner: CalendarDays,
  quizmaster: Brain,
  analyst: Microscope,
  companion: HeartHandshake,
  system: Sparkles,
};

const COLORS: Record<AgentStep["agent"], string> = {
  orchestrator: "text-foreground",
  planner: "text-primary",
  quizmaster: "text-accent",
  analyst: "text-warning",
  companion: "text-success",
  system: "text-muted-foreground",
};

export function AgentTrace({ runId }: { runId: string | null }) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [done, setDone] = useState(false);
  const lastRunId = useRef<string | null>(null);

  useEffect(() => {
    if (!runId || lastRunId.current === runId) return;
    lastRunId.current = runId;
    setSteps([]);
    setDone(false);

    const es = new EventSource(`${API_URL}/stream/agent-trace/${runId}`);
    es.addEventListener("step", (ev) => {
      try {
        const step: AgentStep = JSON.parse((ev as MessageEvent).data);
        setSteps((s) => [...s, step]);
      } catch {
        /* ignore */
      }
    });
    es.addEventListener("done", () => {
      setDone(true);
      es.close();
    });
    es.onerror = () => {
      // Auto-close on error to avoid endless retry loop
      es.close();
      setDone(true);
    };
    return () => es.close();
  }, [runId]);

  if (!runId) {
    return (
      <div className="text-sm text-muted-foreground flex items-center gap-2">
        <Activity className="size-4" />
        Live agent trace will appear here once you start a quiz.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className={`relative size-2 rounded-full ${done ? "bg-muted" : "bg-accent"}`}>
            {!done && <span className="absolute inset-0 rounded-full bg-accent animate-ping opacity-60" />}
          </span>
          {done ? "Trace complete" : "Agents thinking..."}
        </span>
        <Badge variant="outline" className="text-[10px]">{steps.length} steps</Badge>
      </div>
      <div className="rounded-lg border border-border bg-background/30 max-h-[60vh] overflow-y-auto scrollbar-thin">
        <AnimatePresence initial={false}>
          {steps.map((s, i) => {
            const Icon = ICONS[s.agent] ?? Brain;
            return (
              <motion.div
                key={`${runId}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25 }}
                className="flex items-start gap-3 p-3 border-b border-border/40 last:border-b-0"
              >
                <div
                  className={`size-8 rounded-md grid place-items-center bg-input/40 ${COLORS[s.agent]}`}
                >
                  <Icon className="size-4" />
                </div>
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize text-[10px]">
                      {s.agent}
                    </Badge>
                    <div className="text-sm font-medium">{s.headline}</div>
                  </div>
                  {s.detail && (
                    <div className="text-xs text-muted-foreground leading-relaxed">{s.detail}</div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {steps.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground flex items-center gap-2">
            <Activity className="size-4 animate-pulse" />
            Subscribed to <code>{runId.slice(0, 8)}</code> ...
          </div>
        )}
      </div>
    </div>
  );
}
