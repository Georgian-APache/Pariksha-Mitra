"use client";

import * as React from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/cn";

type MotionCardProps = Omit<HTMLMotionProps<"div">, "initial" | "animate" | "transition"> & {
  /** Stagger index - card #i delays its entrance by ``index * 0.05s``. */
  index?: number;
  /** Optional explicit delay (overrides ``index * 0.05``). */
  delay?: number;
};

/**
 * Drop-in replacement for ``<Card>`` that adds a subtle fade-up entrance:
 *   - 8px translate, opacity 0 -> 1
 *   - 0.35s ease-out
 *   - staggered via ``index * 0.05s``
 *
 * Visually identical to ``Card`` (same Tailwind classes) so it slots in
 * anywhere a ``<Card>`` was used.
 */
export function MotionCard({
  index = 0,
  delay,
  className,
  children,
  ...rest
}: MotionCardProps) {
  const computedDelay = delay ?? index * 0.05;
  return (
    <motion.div
      className={cn(
        "rounded-xl border border-border bg-card/60 backdrop-blur-md shadow-[0_1px_0_0_oklch(1_0_0/0.04)_inset]",
        className,
      )}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut", delay: computedDelay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
