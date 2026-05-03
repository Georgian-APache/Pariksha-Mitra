"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Heart } from "lucide-react";

type Props = {
  suggestion: string;
  followUp?: string;
};

export function CopingCard({ suggestion, followUp }: Props) {
  const [open, setOpen] = useState(true);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-[oklch(0.65_0.15_290)]/30 bg-[oklch(0.65_0.15_290)]/8 overflow-hidden"
    >
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left"
      >
        <Heart className="size-4 text-[oklch(0.65_0.15_290)] shrink-0" />
        <span className="text-sm font-medium flex-1">Coping strategy for you</span>
        <ChevronDown
          className={`size-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-2">
              <p className="text-sm text-foreground/80">{suggestion}</p>
              {followUp && (
                <p className="text-xs text-muted-foreground italic">💬 {followUp}</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
