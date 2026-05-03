"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { RealityCheckQuiz } from "@/components/RealityCheckQuiz";
import { Progress } from "@/components/ui/Progress";
import { api } from "@/lib/api";
import { loadKeys } from "@/lib/byok";
import type {
  TodaySchedule, StudySessionItem, Question, RealityCheckResult,
} from "@/lib/types";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: "Pending", color: "text-muted-foreground", icon: <Clock className="size-4" /> },
  quiz_pending: { label: "Quiz", color: "text-amber-500", icon: <Clock className="size-4 text-amber-500" /> },
  completed: { label: "Done", color: "text-green-500", icon: <CheckCircle className="size-4 text-green-500" /> },
  quiz_passed: { label: "Passed", color: "text-green-500", icon: <CheckCircle className="size-4 text-green-500" /> },
  skipped: { label: "Skipped", color: "text-destructive", icon: <XCircle className="size-4 text-destructive" /> },
  quiz_failed: { label: "Failed", color: "text-amber-500", icon: <XCircle className="size-4 text-amber-500" /> },
};

export function ScheduleTracker() {
  const userId = loadKeys().userId;
  const [data, setData] = useState<TodaySchedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [quizSession, setQuizSession] = useState<{ sessionId: string; questions: Question[] } | null>(null);

  const load = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await api<TodaySchedule>(`/schedule/${userId}/today`);
      setData(res);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  async function markStudied(sessionId: string) {
    setActionLoading(sessionId);
    try {
      const res = await api<{ status: string; quiz_questions?: Question[]; session_id?: string }>(
        "/schedule/mark",
        { method: "POST", body: { user_id: userId, session_id: sessionId, studied: true } }
      );
      if (res.quiz_questions) {
        setQuizSession({ sessionId: res.session_id!, questions: res.quiz_questions });
      }
      await load();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setActionLoading(null);
    }
  }

  async function markSkipped(sessionId: string) {
    setActionLoading(sessionId);
    try {
      const res = await api<{ status: string; consecutive_misses?: number; warning?: string }>(
        "/schedule/mark",
        { method: "POST", body: { user_id: userId, session_id: sessionId, studied: false } }
      );
      if (res.warning) toast.warning(res.warning);
      await load();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setActionLoading(null);
    }
  }

  async function submitRealityCheck(
    answers: { question_id: string; chosen_index: number }[]
  ): Promise<RealityCheckResult> {
    const res = await api<RealityCheckResult>("/schedule/submit-reality-check", {
      method: "POST",
      body: { user_id: userId, session_id: quizSession!.sessionId, answers },
    });
    await load();
    return res;
  }

  if (!userId) return <p className="text-sm text-muted-foreground">Complete onboarding to track schedule.</p>;
  if (loading) return <div className="animate-pulse h-40 rounded-xl bg-input/20" />;
  if (!data || !data.sessions.length) return (
    <div className="rounded-xl border border-border p-4 text-sm text-muted-foreground text-center">
      No study sessions for today. Your plan will appear here once generated.
    </div>
  );

  const { sessions, summary, consecutive_misses } = data;
  const pct = summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">Today's Progress</span>
          <span className="text-muted-foreground">{summary.completed}/{summary.total} done</span>
        </div>
        <Progress value={pct} className="h-2" />
        {consecutive_misses >= 1 && (
          <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-3 py-1.5">
            <AlertTriangle className="size-3.5" />
            {consecutive_misses}/2 misses — parent alert triggers at 2
          </div>
        )}
      </div>

      {/* Session list */}
      <div className="space-y-2">
        {sessions.map((s, i) => (
          <SessionRow
            key={s.id}
            session={s}
            index={i}
            actionLoading={actionLoading === s.id}
            onStudied={() => markStudied(s.id)}
            onSkipped={() => markSkipped(s.id)}
          />
        ))}
      </div>

      {/* Reality check quiz modal */}
      {quizSession && (
        <RealityCheckQuiz
          questions={quizSession.questions}
          onSubmit={submitRealityCheck}
          onClose={() => { setQuizSession(null); load(); }}
        />
      )}
    </div>
  );
}

function SessionRow({
  session, index, actionLoading, onStudied, onSkipped,
}: {
  session: StudySessionItem;
  index: number;
  actionLoading: boolean;
  onStudied: () => void;
  onSkipped: () => void;
}) {
  const cfg = STATUS_CONFIG[session.status] ?? STATUS_CONFIG.pending;
  const isPending = session.status === "pending";

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex items-center gap-3 rounded-xl border border-border p-3 bg-background"
    >
      <div className="shrink-0">{cfg.icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{session.concept_id}</p>
        <p className="text-xs text-muted-foreground">
          {session.subject} · {session.activity} · {session.scheduled_minutes}min
        </p>
        {session.quiz_score != null && (
          <p className="text-xs text-muted-foreground">Quiz: {Math.round(session.quiz_score * 100)}%</p>
        )}
      </div>
      {isPending && (
        <div className="flex gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onStudied}
            disabled={actionLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-green-500/10 text-green-600 hover:bg-green-500/20 disabled:opacity-50 transition"
          >
            {actionLoading ? "…" : "✓ Studied"}
          </button>
          <button
            type="button"
            onClick={onSkipped}
            disabled={actionLoading}
            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-destructive/10 text-destructive hover:bg-destructive/20 disabled:opacity-50 transition"
          >
            {actionLoading ? "…" : "✗ Skip"}
          </button>
        </div>
      )}
      {!isPending && (
        <span className={`text-xs font-medium shrink-0 ${cfg.color}`}>{cfg.label}</span>
      )}
    </motion.div>
  );
}
