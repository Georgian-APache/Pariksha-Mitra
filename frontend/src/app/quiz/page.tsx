"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Loader2,
  RefreshCcw,
  Sparkles,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Progress } from "@/components/ui/Progress";
import { AgentTrace } from "@/components/AgentTrace";
import { ExplainSlider, type ExplainLevel } from "@/components/ExplainSlider";
import { Pomodoro } from "@/components/Pomodoro";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";
import type { GradedAnswer, Question } from "@/lib/types";

type StartResponse = {
  session_id: string;
  question: Question;
  progress: { asked: number; answered: number; total: number };
  cat: { level: number };
};

type AnswerResponse = {
  grade: GradedAnswer;
  next_question: Question | null;
  progress: { asked: number; answered: number; total: number };
  cat: { level: number };
  session_complete: boolean;
};

type FinishResponse = {
  user_id: string;
  run_id: string;
  summary: { avg_score: number; n_questions: number; concept_id: string };
  plan: Record<string, unknown>;
  readiness: Record<string, number>;
  nudge: { en?: string; hi?: string };
  weak_prereqs: string[];
  replanned: boolean;
};

function QuizPageInner() {
  const router = useRouter();
  const search = useSearchParams();
  const conceptParam = search.get("concept");
  const [keys] = useApiKeys();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [progress, setProgress] = useState({ asked: 0, answered: 0, total: 8 });
  const [cat, setCat] = useState<{ level: number }>({ level: 3 });
  const [chosen, setChosen] = useState<number | null>(null);
  const [grade, setGrade] = useState<GradedAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [explain, setExplain] = useState<ExplainLevel>("grade10");
  const [completed, setCompleted] = useState(false);
  const [finishResult, setFinishResult] = useState<FinishResponse | null>(null);
  const [traceRunId, setTraceRunId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const startedAt = useRef<number>(0);

  useEffect(() => {
    if (!keys.userId) {
      toast.error("Run the diagnostic first");
      router.replace("/onboarding");
      return;
    }
    const ctrl = new AbortController();
    void start(ctrl.signal);
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keys.userId, conceptParam]);

  async function start(signal?: AbortSignal) {
    setBusy(true);
    setCompleted(false);
    setGrade(null);
    setChosen(null);
    setFinishResult(null);
    setTraceRunId(null);
    setLoadError(null);
    try {
      const res = await api<StartResponse>("/quiz/start", {
        method: "POST",
        body: {
          user_id: keys.userId,
          concept_id: conceptParam || undefined,
          n_questions: 5,
          kind: conceptParam ? "drill" : "adaptive",
        },
        signal,
      });
      if (signal?.aborted) return;
      setSessionId(res.session_id);
      setQuestion(res.question);
      setProgress(res.progress);
      setCat(res.cat);
      startedAt.current = Date.now();
    } catch (err) {
      if ((err as Error)?.name === "AbortError" || signal?.aborted) return;
      const msg = (err as Error).message || "Could not start quiz";
      setLoadError(msg);
      toast.error(msg);
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }

  async function submitAnswer() {
    if (!sessionId || !question || chosen === null) return;
    setBusy(true);
    try {
      const elapsed = Math.round((Date.now() - startedAt.current) / 1000);
      const res = await api<AnswerResponse>("/quiz/answer", {
        method: "POST",
        body: {
          session_id: sessionId,
          question_id: question.id,
          chosen_index: chosen,
          time_taken_s: elapsed,
        },
      });
      setGrade(res.grade);
      setProgress(res.progress);
      setCat(res.cat);
      if (res.session_complete) {
        // Trigger the "Wow Moment" finish flow
        void finishQuiz();
      }
      // Cache next question for the user to advance manually
      setQuestion(res.next_question ?? question);
      // We keep the just-answered question visible until user clicks "Next"
      if (res.next_question) {
        // Stash for advancement
        sessionStorage.setItem("pm.quiz.pending_next", JSON.stringify(res.next_question));
      } else {
        sessionStorage.removeItem("pm.quiz.pending_next");
      }
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function advance() {
    const nextRaw = sessionStorage.getItem("pm.quiz.pending_next");
    sessionStorage.removeItem("pm.quiz.pending_next");
    setChosen(null);
    setGrade(null);
    if (nextRaw) {
      try {
        setQuestion(JSON.parse(nextRaw));
        startedAt.current = Date.now();
      } catch {
        /* ignore */
      }
    }
  }

  async function startMicroQuiz() {
    if (!keys.userId) return;
    const concept = question?.concept_id || conceptParam || undefined;
    setBusy(true);
    setCompleted(false);
    setGrade(null);
    setChosen(null);
    setFinishResult(null);
    setTraceRunId(null);
    try {
      const res = await api<StartResponse>("/quiz/start", {
        method: "POST",
        body: {
          user_id: keys.userId,
          concept_id: concept,
          n_questions: 2,
          kind: "drill",
        },
      });
      setSessionId(res.session_id);
      setQuestion(res.question);
      setProgress(res.progress);
      setCat(res.cat);
      startedAt.current = Date.now();
      toast.message("Break-time micro-quiz", {
        description: "Two quick questions to keep the streak alive.",
      });
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function finishQuiz() {
    if (!sessionId) return;
    setBusy(true);
    try {
      const res = await api<FinishResponse>("/quiz/finish", {
        method: "POST",
        body: { session_id: sessionId },
      });
      setFinishResult(res);
      setTraceRunId(res.run_id);
      setCompleted(true);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const pct = useMemo(
    () => Math.round((progress.answered / Math.max(1, progress.total)) * 100),
    [progress.answered, progress.total],
  );

  return (
    <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
              <Brain className="size-5 text-accent" />
              Adaptive quiz
              {conceptParam && <Badge variant="outline">{conceptParam}</Badge>}
            </h1>
            <p className="text-sm text-muted-foreground">
              CAT-lite difficulty: <span className="font-medium">Level {cat.level}/5</span>
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void start()} disabled={busy}>
            <RefreshCcw className="size-4" /> Restart
          </Button>
        </div>

        <Progress value={pct} />

        {!question ? (
          <Card>
            <CardContent className="p-12 text-center text-muted-foreground space-y-3">
              {loadError ? (
                <>
                  <p className="text-sm font-medium text-destructive">Could not start the quiz</p>
                  <p className="text-xs">{loadError}</p>
                  <Button onClick={() => void start()} disabled={busy}>Retry</Button>
                </>
              ) : (
                <>
                  <Loader2 className="size-5 animate-spin mx-auto mb-3" />
                  Generating your first question...
                </>
              )}
            </CardContent>
          </Card>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={question.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <Card>
                <CardContent className="p-6 space-y-5">
                  <div className="flex flex-wrap gap-2 items-center justify-between">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{question.subject}</Badge>
                      <Badge variant="default">{question.concept_id}</Badge>
                      <Badge variant="warning">Difficulty {question.difficulty}/5</Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      Q {progress.answered + 1} of {progress.total}
                    </span>
                  </div>

                  <h2 className="text-lg font-medium leading-relaxed">{question.stem}</h2>

                  <div className="grid sm:grid-cols-2 gap-2">
                    {question.options.map((opt, i) => {
                      const selected = chosen === i;
                      const correctness =
                        grade && grade.question_id === question.id
                          ? i === question.correct_index
                            ? "correct"
                            : selected
                              ? "wrong"
                              : "muted"
                          : "neutral";
                      return (
                        <button
                          key={i}
                          onClick={() => !grade && setChosen(i)}
                          disabled={!!grade}
                          className={`text-left rounded-lg border px-4 py-3 transition ${
                            correctness === "correct"
                              ? "border-success bg-success/10"
                              : correctness === "wrong"
                                ? "border-destructive bg-destructive/10"
                                : selected
                                  ? "border-primary bg-primary/10"
                                  : "border-border hover:border-primary/40 hover:bg-input/40"
                          }`}
                        >
                          <div className="text-xs text-muted-foreground mb-0.5">
                            ({String.fromCharCode(65 + i)})
                          </div>
                          <div className="text-sm">{opt}</div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <ExplainSlider value={explain} onChange={setExplain} />
                    {!grade ? (
                      <Button
                        onClick={submitAnswer}
                        disabled={chosen === null || busy}
                        size="lg"
                      >
                        {busy ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />} Submit
                      </Button>
                    ) : completed ? (
                      <Button asChild size="lg">
                        <Link href="/dashboard">View dashboard <ArrowRight className="size-4" /></Link>
                      </Button>
                    ) : (
                      <Button onClick={advance} size="lg" disabled={busy}>
                        Next question <ArrowRight className="size-4" />
                      </Button>
                    )}
                  </div>

                  <AnimatePresence>
                    {grade && grade.question_id === question.id && (
                      <motion.div
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`rounded-lg border px-4 py-3 text-sm ${
                          grade.correct
                            ? "border-success/40 bg-success/5 text-success"
                            : "border-warning/40 bg-warning/5 text-warning"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          {grade.correct ? <CheckCircle2 className="size-4 mt-0.5" /> : <XCircle className="size-4 mt-0.5" />}
                          <div>
                            <div className="font-medium">
                              {grade.correct ? "Correct" : `Partial credit: ${(grade.score * 100).toFixed(0)}%`}
                            </div>
                            <div className="text-foreground/80 mt-1">{grade.rationale}</div>
                            {grade.misconception && (
                              <div className="text-xs mt-1 italic">Likely misconception: {grade.misconception}</div>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
            </motion.div>
          </AnimatePresence>
        )}

        {completed && finishResult && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="border-accent/40 bg-accent/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="size-5 text-accent" /> The agents replanned
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Score:</span> {(finishResult.summary.avg_score * 100).toFixed(0)}%
                  {" | "}
                  <span className="font-medium">Readiness now:</span> {finishResult.readiness?.readiness?.toFixed?.(1)}
                </div>
                {finishResult.weak_prereqs.length > 0 && (
                  <div className="text-warning">
                    Weak prerequisites flagged: {finishResult.weak_prereqs.join(", ")}
                  </div>
                )}
                {finishResult.nudge?.en && (
                  <div className="text-foreground/80 mt-2">{finishResult.nudge.en}</div>
                )}
                {finishResult.nudge?.hi && (
                  <div className="text-muted-foreground">{finishResult.nudge.hi}</div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>

      <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <Pomodoro onBreakStart={startMicroQuiz} />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-accent" /> Live agent trace
            </CardTitle>
          </CardHeader>
          <CardContent>
            <AgentTrace runId={traceRunId} />
            {!traceRunId && (
              <p className="text-xs text-muted-foreground mt-3">
                Finish the quiz - or trigger a manual replan from the dashboard - to watch
                the LangGraph agents reason in real time.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<div className="p-12 text-muted-foreground">Loading...</div>}>
      <QuizPageInner />
    </Suspense>
  );
}
