"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Progress } from "@/components/ui/Progress";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";
import type { DiagnosticSubmitResponse, Question } from "@/lib/types";

export default function DiagnosticPage() {
  const router = useRouter();
  const [keys] = useApiKeys();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [idx, setIdx] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("pm.diagnostic.questions");
    if (!raw) {
      router.replace("/onboarding");
      return;
    }
    try {
      setQuestions(JSON.parse(raw) as Question[]);
    } catch {
      router.replace("/onboarding");
    }
  }, [router]);

  const total = questions.length;
  const cur = questions[idx];
  const progress = useMemo(() => Math.round(((idx) / Math.max(1, total)) * 100), [idx, total]);

  function pick(answer: number) {
    if (!cur) return;
    setAnswers((a) => ({ ...a, [cur.id]: answer }));
  }

  function next() {
    if (idx < total - 1) setIdx(idx + 1);
  }

  async function submit() {
    if (!keys.userId) {
      toast.error("Missing user id - restart onboarding");
      router.replace("/onboarding");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        user_id: keys.userId,
        questions,
        answers: questions.map((q) => ({
          question_id: q.id,
          chosen_index: answers[q.id] ?? -1,
        })),
      };
      const res = await api<DiagnosticSubmitResponse>("/onboard/submit", {
        method: "POST",
        body: payload,
      });
      sessionStorage.removeItem("pm.diagnostic.questions");
      sessionStorage.setItem("pm.last_run_id", res.run_id);
      sessionStorage.setItem("pm.last_nudge", JSON.stringify(res.nudge));
      router.push("/dashboard");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!cur) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-12">
        <Loader2 className="size-4 animate-spin" /> Loading questions...
      </div>
    );
  }

  const allAnswered = questions.every((q) => answers[q.id] !== undefined);
  const last = idx === total - 1;
  const chosen = answers[cur.id];

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Diagnostic - calibrating your knowledge graph</span>
          <span>{idx + 1} / {total}</span>
        </div>
        <Progress value={progress} />
      </div>

      <motion.div
        key={cur.id}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <Card>
          <CardContent className="p-6 space-y-5">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{cur.subject}</Badge>
              <Badge variant="default">{cur.concept_id}</Badge>
              <Badge variant="warning">Difficulty {cur.difficulty}/5</Badge>
            </div>
            <h2 className="text-xl font-medium leading-snug">{cur.stem}</h2>
            <div className="grid sm:grid-cols-2 gap-2">
              {cur.options.map((opt, i) => {
                const selected = chosen === i;
                return (
                  <button
                    key={i}
                    onClick={() => pick(i)}
                    className={`text-left rounded-lg border px-4 py-3 transition ${
                      selected
                        ? "border-primary bg-primary/10 ring-1 ring-primary/40"
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
          </CardContent>
        </Card>
      </motion.div>

      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => setIdx(Math.max(0, idx - 1))}
          disabled={idx === 0}
        >
          Previous
        </Button>
        {last ? (
          <Button onClick={submit} disabled={!allAnswered || submitting} size="lg">
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Crunching with the agents...
              </>
            ) : (
              <>
                <Sparkles className="size-4" /> Submit + generate plan
                <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        ) : (
          <Button onClick={next} disabled={chosen === undefined}>
            Next <ArrowRight className="size-4" />
          </Button>
        )}
      </div>
      <div className="text-xs text-muted-foreground flex items-center gap-1.5">
        <CheckCircle2 className="size-3" />
        Your answers stay in your browser; only summary mastery is sent to the agents.
      </div>
    </div>
  );
}
