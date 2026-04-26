"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, RotateCcw, Coffee, Brain } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

type Phase = "focus" | "break";

const FOCUS_SECONDS = 25 * 60;
const BREAK_SECONDS = 5 * 60;

export type PomodoroProps = {
  /** Fired exactly when the timer transitions from focus -> break. */
  onBreakStart?: () => void;
  /** Fired exactly when the timer transitions from break -> focus. */
  onFocusStart?: () => void;
  className?: string;
};

function fmt(s: number): string {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

/**
 * Synth a short two-tone chime via the Web Audio API. No asset required.
 * Falls back silently if the AudioContext is unavailable (SSR / locked-down browsers).
 */
function chime(kind: Phase) {
  if (typeof window === "undefined") return;
  const Ctx = (window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext) as typeof AudioContext | undefined;
  if (!Ctx) return;
  try {
    const ctx = new Ctx();
    const now = ctx.currentTime;
    const tones = kind === "break" ? [880, 1320] : [660, 990];
    tones.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const t0 = now + i * 0.18;
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(0.18, t0 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.32);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t0);
      osc.stop(t0 + 0.34);
    });
    setTimeout(() => ctx.close().catch(() => {}), 1200);
  } catch {
    /* no-op */
  }
}

export function Pomodoro({ onBreakStart, onFocusStart, className }: PomodoroProps) {
  const [phase, setPhase] = useState<Phase>("focus");
  const [running, setRunning] = useState(false);
  const [remaining, setRemaining] = useState(FOCUS_SECONDS);
  const [cycles, setCycles] = useState(0);
  const breakStartRef = useRef(onBreakStart);
  const focusStartRef = useRef(onFocusStart);

  useEffect(() => {
    breakStartRef.current = onBreakStart;
  }, [onBreakStart]);
  useEffect(() => {
    focusStartRef.current = onFocusStart;
  }, [onFocusStart]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      setRemaining((r) => Math.max(0, r - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [running]);

  // Phase transition when remaining hits 0
  useEffect(() => {
    if (remaining > 0) return;
    if (phase === "focus") {
      chime("break");
      setPhase("break");
      setRemaining(BREAK_SECONDS);
      setCycles((c) => c + 1);
      breakStartRef.current?.();
    } else {
      chime("focus");
      setPhase("focus");
      setRemaining(FOCUS_SECONDS);
      focusStartRef.current?.();
    }
  }, [remaining, phase]);

  const total = phase === "focus" ? FOCUS_SECONDS : BREAK_SECONDS;
  const pct = 1 - remaining / total;

  const reset = useCallback(() => {
    setRunning(false);
    setPhase("focus");
    setRemaining(FOCUS_SECONDS);
  }, []);

  const skip = useCallback(() => {
    setRemaining(0);
  }, []);

  // Ring geometry
  const size = 132;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * pct;

  const ringColor = phase === "focus" ? "stroke-primary" : "stroke-success";
  const tintBg = phase === "focus" ? "bg-primary/10" : "bg-success/10";

  return (
    <Card className={className}>
      <CardHeader className="pb-1">
        <CardTitle className="flex items-center gap-2">
          {phase === "focus" ? (
            <Brain className="size-4 text-primary" />
          ) : (
            <Coffee className="size-4 text-success" />
          )}
          Pomodoro
          <Badge
            variant={phase === "focus" ? "default" : "success"}
            className="ml-auto"
          >
            {phase === "focus" ? "Focus" : "Break"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-3">
        <div className={cn("relative grid place-items-center rounded-full", tintBg)} style={{ width: size, height: size }}>
          <svg width={size} height={size} className="-rotate-90">
            <circle
              cx={size / 2}
              cy={size / 2}
              r={r}
              strokeWidth={stroke}
              className="stroke-border"
              fill="none"
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={r}
              strokeWidth={stroke}
              className={cn(ringColor, "transition-[stroke-dashoffset] duration-1000 ease-linear")}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={c}
              strokeDashoffset={c - dash}
            />
          </svg>
          <div className="absolute inset-0 grid place-items-center">
            <div className="text-center">
              <div className="font-mono text-2xl tabular-nums">{fmt(remaining)}</div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                {phase === "focus" ? "deep work" : "micro break"}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!running ? (
            <Button size="sm" onClick={() => setRunning(true)}>
              <Play className="size-4" /> Start
            </Button>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setRunning(false)}>
              <Pause className="size-4" /> Pause
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={skip} title="Skip phase">
            Skip
          </Button>
          <Button size="sm" variant="ghost" onClick={reset} title="Reset">
            <RotateCcw className="size-4" />
          </Button>
        </div>

        <p className="text-xs text-muted-foreground text-center">
          {cycles > 0
            ? `Completed ${cycles} cycle${cycles === 1 ? "" : "s"}. Breaks pop a 2-Q micro-quiz.`
            : "25 min focus / 5 min break. Breaks pop a 2-Q micro-quiz."}
        </p>
      </CardContent>
    </Card>
  );
}
