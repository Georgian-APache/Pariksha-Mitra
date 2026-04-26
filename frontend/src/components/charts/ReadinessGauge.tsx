"use client";

import { motion } from "framer-motion";

export function ReadinessGauge({ value, label = "Readiness" }: { value: number; label?: string }) {
  const v = Math.max(0, Math.min(100, value));
  const radius = 70;
  const circumference = Math.PI * radius; // half-circle
  const stroke = 12;
  const arcLen = (v / 100) * circumference;
  return (
    <div className="relative w-full max-w-[260px] aspect-[2/1.05] mx-auto">
      <svg viewBox="0 0 200 110" className="w-full h-full">
        <defs>
          <linearGradient id="gauge-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="oklch(0.62 0.2 280)" />
            <stop offset="50%" stopColor="oklch(0.78 0.16 200)" />
            <stop offset="100%" stopColor="oklch(0.7 0.18 150)" />
          </linearGradient>
        </defs>
        <path
          d={`M ${100 - radius} 100 A ${radius} ${radius} 0 0 1 ${100 + radius} 100`}
          fill="none"
          stroke="oklch(1 0 0 / 0.08)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <motion.path
          d={`M ${100 - radius} 100 A ${radius} ${radius} 0 0 1 ${100 + radius} 100`}
          fill="none"
          stroke="url(#gauge-grad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - arcLen }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
        <div className="text-4xl font-semibold tabular-nums">{Math.round(v)}</div>
        <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      </div>
    </div>
  );
}
