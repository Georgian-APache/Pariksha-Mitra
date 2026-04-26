"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Loader2,
  Sparkles,
  RefreshCcw,
  Camera,
  Network,
  Brain,
  Lightbulb,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { MotionCard } from "@/components/MotionCard";
import { ReadinessGauge } from "@/components/charts/ReadinessGauge";
import { SubjectRadar } from "@/components/charts/SubjectRadar";
import { TrendChart } from "@/components/charts/TrendChart";
import { RankPredictor } from "@/components/charts/RankPredictor";
import { PlanStrip } from "@/components/PlanStrip";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";
import type { Dashboard } from "@/lib/types";

type Insight = {
  insight_en: string;
  insight_hi: string;
  generated_at: string;
};

export default function DashboardPage() {
  const [keys] = useApiKeys();
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [replaning, setReplaning] = useState(false);
  const [nudge, setNudge] = useState<{ en?: string; hi?: string } | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);

  async function load() {
    if (!keys.userId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const d = await api<Dashboard>(`/plan/${keys.userId}/dashboard`);
      setData(d);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function loadInsight() {
    if (!keys.userId || !keys.gemini) return;
    setInsightLoading(true);
    try {
      const i = await api<Insight>("/insights/dashboard", {
        method: "POST",
        body: { user_id: keys.userId },
      });
      setInsight(i);
    } catch {
      // Silently fail - the dashboard is usable without the AI blurb.
    } finally {
      setInsightLoading(false);
    }
  }

  useEffect(() => {
    load();
    const lastNudge = sessionStorage.getItem("pm.last_nudge");
    if (lastNudge) {
      try {
        setNudge(JSON.parse(lastNudge));
      } catch {
        /* ignore */
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keys.userId]);

  useEffect(() => {
    loadInsight();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keys.userId, keys.gemini]);

  async function replan() {
    if (!keys.userId) return;
    setReplaning(true);
    try {
      const res = await api<{ run_id: string; nudge: { en?: string; hi?: string } }>("/plan/replan", {
        method: "POST",
        body: { user_id: keys.userId },
      });
      sessionStorage.setItem("pm.last_run_id", res.run_id);
      setNudge(res.nudge);
      await load();
      toast.success("Plan refreshed by the agents");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setReplaning(false);
    }
  }

  if (!keys.userId) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center space-y-4">
        <Sparkles className="size-8 text-accent mx-auto" />
        <h2 className="text-xl font-semibold">No profile yet</h2>
        <p className="text-muted-foreground">
          Run the diagnostic so the agents can build your knowledge graph.
        </p>
        <Button asChild>
          <Link href="/onboarding">Start diagnostic</Link>
        </Button>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-12">
        <Loader2 className="size-4 animate-spin" /> Loading dashboard...
      </div>
    );
  }

  const r = data.readiness;

  return (
    <div className="space-y-6 py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your study dashboard</h1>
          <p className="text-sm text-muted-foreground">
            {data.target_exam.replace("_", " ")} {" | "} {data.daily_hours}h/day
            {data.exam_date ? ` | exam ${data.exam_date}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs sm:text-sm">
          <Button variant="outline" size="sm" asChild>
            <Link href="/quiz"><Brain className="size-4" /> Adaptive quiz</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/doubt"><Camera className="size-4" /> Snap a doubt</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/graph"><Network className="size-4" /> Concept graph</Link>
          </Button>
          <Button size="sm" onClick={replan} disabled={replaning}>
            {replaning ? <Loader2 className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
            Re-run agents
          </Button>
        </div>
      </div>

      {(nudge?.en || nudge?.hi) && (
        <MotionCard index={0} className="border-accent/40 bg-accent/5">
          <CardContent className="p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-accent">
              <Sparkles className="size-3.5" /> Companion agent
            </div>
            {nudge.en && <p className="text-sm">{nudge.en}</p>}
            {nudge.hi && <p className="text-sm text-muted-foreground">{nudge.hi}</p>}
          </CardContent>
        </MotionCard>
      )}

      {(insight || insightLoading) && (
        <MotionCard index={1} className="border-primary/40 bg-primary/5">
          <CardContent className="p-5 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-primary">
                <Lightbulb className="size-3.5" /> AI insight
              </div>
              {insightLoading && (
                <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
              )}
            </div>
            {insight ? (
              <>
                <p className="text-sm">{insight.insight_en}</p>
                <p className="text-sm text-muted-foreground">{insight.insight_hi}</p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Generating today&apos;s coaching blurb&hellip;
              </p>
            )}
          </CardContent>
        </MotionCard>
      )}

      <div className="grid lg:grid-cols-3 gap-4">
        <MotionCard index={2}>
          <CardHeader>
            <CardTitle>Exam readiness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ReadinessGauge value={r.readiness} />
            <div className="grid grid-cols-4 gap-2 text-xs">
              <Stat label="Coverage" value={r.coverage} />
              <Stat label="Mastery" value={r.mastery} />
              <Stat label="Revision" value={r.revision} />
              <Stat label="Trend" value={r.mock_trend} />
            </div>
          </CardContent>
        </MotionCard>

        <MotionCard index={3}>
          <CardHeader>
            <CardTitle>Subject mastery</CardTitle>
          </CardHeader>
          <CardContent>
            <SubjectRadar data={data.subject_mastery} />
          </CardContent>
        </MotionCard>

        <MotionCard index={4}>
          <CardHeader>
            <CardTitle>Predicted exam-day percentile</CardTitle>
          </CardHeader>
          <CardContent>
            <RankPredictor prediction={data.rank_prediction} />
          </CardContent>
        </MotionCard>
      </div>

      <MotionCard index={5}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>This week&apos;s plan</CardTitle>
            <Badge variant="outline">{data.plan?.days?.length ?? 0} days</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <PlanStrip plan={data.plan} />
        </CardContent>
      </MotionCard>

      <MotionCard index={6}>
        <CardHeader>
          <CardTitle>Readiness trend</CardTitle>
        </CardHeader>
        <CardContent>
          <TrendChart history={data.readiness_history} />
        </CardContent>
      </MotionCard>

      <div className="text-center text-xs text-muted-foreground">
        Want voice mode, study chat or PDF-RAG? Try{" "}
        <Link href="/quiz" className="text-accent hover:underline">an adaptive quiz</Link>{" "}
        or{" "}
        <Link href="/library" className="text-accent hover:underline">upload an NCERT chapter</Link>.
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-background/40 p-2 text-center">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-semibold tabular-nums">{Math.round(value * 100)}</div>
    </div>
  );
}
