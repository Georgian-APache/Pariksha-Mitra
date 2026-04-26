"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Flame, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { IcsExportButton } from "@/components/IcsExportButton";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";
import { cn } from "@/lib/cn";

type UserSnapshot = {
  id: string;
  display_name: string;
  exam_date: string | null;
  streak_days: number;
};

function daysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const target = new Date(dateStr + "T00:00:00");
  if (Number.isNaN(target.getTime())) return null;
  const now = new Date();
  return Math.max(
    0,
    Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)),
  );
}

export type StreakHudProps = {
  className?: string;
  /** Hide the ICS download button (e.g. on the dashboard where we show it elsewhere). */
  hideIcs?: boolean;
};

/**
 * Streak count + days-to-exam countdown + ICS export.
 * Replaces the inline streak/exam badges previously rendered inside <Header />.
 */
export function StreakHud({ className, hideIcs }: StreakHudProps) {
  const [keys] = useApiKeys();
  const [user, setUser] = useState<UserSnapshot | null>(null);

  useEffect(() => {
    if (!keys.userId) {
      setUser(null);
      return;
    }
    let cancelled = false;
    api<UserSnapshot>(`/users/${keys.userId}`)
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, [keys.userId]);

  if (!user) return null;
  const dToExam = daysUntil(user.exam_date);
  const streak = user.streak_days || 0;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {streak > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <Badge variant="warning" className="gap-1" title={`${streak}-day streak`}>
            <motion.span
              animate={{ rotate: [-6, 6, -4, 4, 0], scale: [1, 1.08, 1, 1.05, 1] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              className="inline-flex"
            >
              <Flame className="size-3" />
            </motion.span>
            {streak}d streak
          </Badge>
        </motion.div>
      )}
      {dToExam !== null && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.05 }}
        >
          <Badge variant="accent" title={`Exam on ${user.exam_date}`}>
            <Sparkles className="size-3 mr-1" /> {dToExam}d to exam
          </Badge>
        </motion.div>
      )}
      {!hideIcs && <IcsExportButton userId={user.id} label="ICS" />}
    </div>
  );
}
