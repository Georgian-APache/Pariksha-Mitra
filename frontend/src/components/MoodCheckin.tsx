"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";

const EMOJIS = ["😢", "😟", "😕", "😐", "🙂", "😊", "😄", "😁", "🤩", "🥳"];
const MOOD_TAGS = ["anxious", "overwhelmed", "tired", "focused", "motivated", "hopeful", "burned_out", "confident"];

type Props = {
  onSubmit: (score: number, tags: string[], note: string) => void;
  loading?: boolean;
};

export function MoodCheckin({ onSubmit, loading }: Props) {
  const [score, setScore] = useState(5);
  const [tags, setTags] = useState<string[]>([]);
  const [note, setNote] = useState("");

  const toggleTag = (t: string) =>
    setTags((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);

  return (
    <div className="space-y-5">
      <div className="text-center">
        <motion.div
          key={score}
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className="text-6xl mb-2"
        >
          {EMOJIS[score - 1]}
        </motion.div>
        <p className="text-sm text-muted-foreground">
          Mood: <span className="font-semibold text-[oklch(0.65_0.15_290)]">{score}/10</span>
        </p>
      </div>

      <input
        type="range" min={1} max={10} value={score}
        onChange={(e) => setScore(Number(e.target.value))}
        className="w-full accent-[oklch(0.65_0.15_290)]"
      />

      <div className="flex flex-wrap gap-2">
        {MOOD_TAGS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => toggleTag(t)}
            className={`px-3 py-1 rounded-full text-xs border transition-all ${
              tags.includes(t)
                ? "bg-[oklch(0.65_0.15_290)] text-white border-transparent"
                : "border-border hover:bg-input/40"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="How are you feeling? (optional)"
        rows={2}
        className="w-full rounded-md border border-border bg-input/20 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-[oklch(0.65_0.15_290)]"
      />

      <Button
        className="w-full bg-[oklch(0.65_0.15_290)] hover:bg-[oklch(0.58_0.17_290)] text-white"
        onClick={() => onSubmit(score, tags, note)}
        disabled={loading}
      >
        {loading ? "Checking in…" : "Share with MindMitra"}
      </Button>
    </div>
  );
}
