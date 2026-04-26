"use client";

import { useEffect, useState } from "react";
import { Moon, Sun, MonitorCog } from "lucide-react";
import {
  applyTheme,
  loadThemePreference,
  nextThemePreference,
  saveThemePreference,
  type ThemePreference,
} from "@/lib/theme";

const LABEL: Record<ThemePreference, string> = {
  dark: "Dark theme",
  light: "Light theme",
  system: "System theme",
};

function Icon({ pref }: { pref: ThemePreference }) {
  if (pref === "light") return <Sun className="size-4" />;
  if (pref === "system") return <MonitorCog className="size-4" />;
  return <Moon className="size-4" />;
}

export function ThemeToggle() {
  const [pref, setPref] = useState<ThemePreference>("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const initial = loadThemePreference();
    setPref(initial);
    applyTheme(initial);
    setMounted(true);

    const onUpdate = (e: Event) => {
      const detail = (e as CustomEvent<ThemePreference>).detail;
      if (detail) {
        setPref(detail);
        applyTheme(detail);
      }
    };
    window.addEventListener("pm:theme-updated", onUpdate);

    const mql = window.matchMedia?.("(prefers-color-scheme: light)");
    const onSystem = () => {
      const cur = loadThemePreference();
      if (cur === "system") applyTheme("system");
    };
    mql?.addEventListener?.("change", onSystem);

    return () => {
      window.removeEventListener("pm:theme-updated", onUpdate);
      mql?.removeEventListener?.("change", onSystem);
    };
  }, []);

  function cycle() {
    const next = nextThemePreference(pref);
    setPref(next);
    saveThemePreference(next);
    applyTheme(next);
  }

  if (!mounted) return null;

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${LABEL[pref]}. Click to change.`}
      title={`${LABEL[pref]} (click to cycle)`}
      className="fixed bottom-4 left-4 z-50 inline-flex items-center gap-2 rounded-full border border-border bg-card/80 backdrop-blur-md px-3 py-2 text-xs font-medium text-foreground shadow-lg shadow-black/20 hover:bg-input/60 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Icon pref={pref} />
      <span className="hidden sm:inline capitalize">{pref}</span>
    </button>
  );
}
