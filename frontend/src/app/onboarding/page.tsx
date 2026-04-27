"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, GraduationCap, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api } from "@/lib/api";
import { saveKeys, useApiKeys } from "@/lib/byok";
import type { DiagnosticStartResponse } from "@/lib/types";

type ExamChoice = "JEE_MAIN" | "NEET" | "GATE" | "OTHER";

const EXAM_OPTIONS: { id: ExamChoice; label: string }[] = [
  { id: "JEE_MAIN", label: "JEE Main" },
  { id: "NEET", label: "NEET UG" },
  { id: "GATE", label: "GATE" },
  { id: "OTHER", label: "Other" },
];

function buildTargetExam(choice: ExamChoice, custom: string): string {
  if (choice === "OTHER") {
    const t = custom.trim().slice(0, 120);
    return t.length > 0 ? t : "Custom exam";
  }
  return choice;
}

export default function OnboardingPage() {
  const [keys] = useApiKeys();
  const router = useRouter();
  const [name, setName] = useState("Student");
  const [examChoice, setExamChoice] = useState<ExamChoice>("JEE_MAIN");
  const [customExam, setCustomExam] = useState("");
  const [examDate, setExamDate] = useState("2026-04-19");
  const [hours, setHours] = useState(3);
  const [loading, setLoading] = useState(false);

  async function startDiagnostic() {
    if (examChoice === "OTHER" && !customExam.trim()) {
      toast.error("Enter your exam name, or pick JEE / NEET / GATE.");
      return;
    }
    setLoading(true);
    try {
      const res = await api<DiagnosticStartResponse>("/onboard/start", {
        method: "POST",
        body: {
          display_name: name,
          target_exam: buildTargetExam(examChoice, customExam),
          exam_date: examDate,
          daily_hours: hours,
          user_id: keys.userId || undefined,
        },
      });
      saveKeys({ userId: res.user_id });
      sessionStorage.setItem("pm.diagnostic.questions", JSON.stringify(res.questions));
      router.push("/onboarding/diagnostic");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      <div className="space-y-2">
        <Badge variant="outline" className="text-xs">Step 1 of 2</Badge>
        <h1 className="text-3xl font-semibold tracking-tight">Tell us about your exam</h1>
        <p className="text-muted-foreground">
          We will run a 15-question calibration spanning your subjects. Takes ~7
          minutes. Use it as a benchmark - the agents will recalibrate as you
          practise.
        </p>
      </div>

      <Card>
        <CardContent className="p-6 space-y-5">
          <div className="space-y-2">
            <Label htmlFor="name">Your name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label>Target exam</Label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {EXAM_OPTIONS.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setExamChoice(id)}
                  className={`h-10 rounded-md border text-sm transition px-2 ${
                    examChoice === id
                      ? "border-primary bg-primary/15 text-primary"
                      : "border-border hover:bg-input/40"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            {examChoice === "OTHER" && (
              <div className="space-y-1.5 pt-1">
                <Label htmlFor="custom-exam" className="text-xs text-muted-foreground">
                  Exam name (e.g. CAT, UPSC CSE, State CET)
                </Label>
                <Input
                  id="custom-exam"
                  placeholder="Type your exam name"
                  value={customExam}
                  onChange={(e) => setCustomExam(e.target.value)}
                  maxLength={120}
                />
                <p className="text-xs text-muted-foreground">
                  Uses the same subject graph as JEE for planning and diagnostics (NEET keeps the biology-heavy graph).
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="date">Exam date</Label>
              <Input
                id="date"
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="hours">
              Daily study hours: <span className="font-medium">{hours}h</span>
            </Label>
            <input
              id="hours"
              type="range"
              min={1}
              max={10}
              step={0.5}
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="w-full accent-[oklch(0.62_0.2_280)]"
            />
            <div className="text-xs text-muted-foreground">
              Block size will scale; target around 60-90 min per concept block.
            </div>
          </div>

          <Button
            size="lg"
            className="w-full"
            onClick={startDiagnostic}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Generating questions...
              </>
            ) : (
              <>
                <GraduationCap className="size-4" /> Start 15-question diagnostic
                <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
