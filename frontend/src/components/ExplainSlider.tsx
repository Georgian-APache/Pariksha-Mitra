"use client";

import { Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export type ExplainLevel = "fiveYearOld" | "grade10" | "iitPrep" | "hindiOnly";

const LEVELS: { id: ExplainLevel; label: string; hint: string }[] = [
  { id: "fiveYearOld", label: "5-yr-old", hint: "tiny analogies" },
  { id: "grade10", label: "Grade 10", hint: "NCERT vibes" },
  { id: "iitPrep", label: "IIT prep", hint: "rigour" },
  { id: "hindiOnly", label: "Hindi", hint: "हिंदी में" },
];

export function ExplainSlider({
  value,
  onChange,
}: {
  value: ExplainLevel;
  onChange: (v: ExplainLevel) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Sparkles className="size-3 text-accent" />
        Explain like:
      </div>
      <div className="flex flex-wrap gap-2">
        {LEVELS.map((l) => (
          <button
            key={l.id}
            onClick={() => onChange(l.id)}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${
              value === l.id
                ? "border-accent bg-accent/15 text-accent"
                : "border-border hover:bg-input/40"
            }`}
            title={l.hint}
          >
            {l.label}
          </button>
        ))}
        <Badge variant="outline" className="text-[10px]">
          {LEVELS.find((l) => l.id === value)?.hint}
        </Badge>
      </div>
    </div>
  );
}
