"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, XCircle, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Progress } from "@/components/ui/Progress";
import type { Question, RealityCheckResult } from "@/lib/types";

type Props = {
  questions: Question[];
  onSubmit: (answers: { question_id: string; chosen_index: number }[]) => Promise<RealityCheckResult>;
  onClose: () => void;
};

export function RealityCheckQuiz({ questions, onSubmit, onClose }: Props) {
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<Record<string, number>>({});
  const [result, setResult] = useState<RealityCheckResult | null>(null);
  const [loading, setLoading] = useState(false);

  const q = questions[current];
  const answered = Object.keys(selected).length;

  async function handleFinish() {
    setLoading(true);
    try {
      const answers = Object.entries(selected).map(([question_id, chosen_index]) => ({
        question_id,
        chosen_index,
      }));
      const res = await onSubmit(answers);
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    const pct = Math.round(result.score * 100);
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-background rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl"
        >
          <div className="text-center space-y-2">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, delay: 0.1 }}
              className="text-5xl"
            >
              {result.passed ? "🎉" : "📚"}
            </motion.div>
            <h2 className="text-xl font-semibold">
              {result.passed ? "Reality Check Passed!" : "Keep Revising"}
            </h2>
            <p className="text-3xl font-bold text-[oklch(0.65_0.15_290)]">{pct}%</p>
            <Progress value={pct} className="h-3" />
          </div>
          <p className="text-sm text-center text-muted-foreground">{result.feedback_en}</p>
          <p className="text-xs text-center text-muted-foreground italic">{result.feedback_hi}</p>
          {/* Wrong answers review */}
          {result.graded_answers.filter((a) => !a.correct).length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Questions to revisit:</p>
              {result.graded_answers.filter((a) => !a.correct).map((a, i) => (
                <div key={i} className="text-xs p-2 rounded-lg bg-destructive/5 border border-destructive/20">
                  <span className="text-destructive">✗ </span>{a.rationale || "Review this concept."}
                </div>
              ))}
            </div>
          )}
          <Button className="w-full" onClick={onClose}>Done</Button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-background rounded-2xl p-6 max-w-lg w-full space-y-5 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-lg">Reality Check Quiz</h2>
            <p className="text-xs text-muted-foreground">{answered}/{questions.length} answered</p>
          </div>
          <button type="button" onClick={onClose} className="size-8 rounded-full hover:bg-input/40 flex items-center justify-center">
            <X className="size-4" />
          </button>
        </div>

        <Progress value={(current / questions.length) * 100} className="h-1.5" />

        {/* Question navigator */}
        <div className="flex gap-1.5 flex-wrap">
          {questions.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setCurrent(i)}
              className={`size-7 rounded-full text-xs font-medium transition ${
                i === current
                  ? "bg-[oklch(0.65_0.15_290)] text-white"
                  : selected[questions[i].id] !== undefined
                  ? "bg-[oklch(0.65_0.15_290)]/20 text-[oklch(0.65_0.15_290)]"
                  : "bg-input/30"
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>

        {/* Question card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, x: 15 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -15 }}
            className="space-y-3"
          >
            <div className="flex items-start gap-2">
              <span className="text-xs text-muted-foreground mt-0.5 shrink-0">Q{current + 1}.</span>
              <p className="text-sm font-medium leading-relaxed">{q.stem}</p>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {q.options.map((opt, idx) => {
                const sel = selected[q.id] === idx;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelected((prev) => ({ ...prev, [q.id]: idx }))}
                    className={`text-left px-4 py-2.5 rounded-xl border text-sm transition ${
                      sel
                        ? "border-[oklch(0.65_0.15_290)] bg-[oklch(0.65_0.15_290)]/10 text-[oklch(0.45_0.15_290)]"
                        : "border-border hover:bg-input/30"
                    }`}
                  >
                    <span className="font-medium mr-2">{String.fromCharCode(65 + idx)}.</span>
                    {opt}
                  </button>
                );
              })}
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex gap-2">
          {current > 0 && (
            <Button variant="outline" className="flex-1" onClick={() => setCurrent((c) => c - 1)}>
              Previous
            </Button>
          )}
          {current < questions.length - 1 ? (
            <Button
              className="flex-1"
              onClick={() => setCurrent((c) => c + 1)}
              disabled={selected[q.id] === undefined}
            >
              Next
            </Button>
          ) : (
            <Button
              className="flex-1 bg-[oklch(0.65_0.15_290)] hover:bg-[oklch(0.58_0.17_290)] text-white"
              onClick={handleFinish}
              disabled={answered < questions.length || loading}
            >
              {loading ? "Grading…" : "Submit Quiz"}
            </Button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
