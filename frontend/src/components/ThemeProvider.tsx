"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { applyTheme, loadThemePreference } from "@/lib/theme";

/**
 * Thin client-only host that:
 *   1. Applies the saved theme preference as early as possible (avoids the
 *      brief flash where the document is still in the default dark mode).
 *   2. Renders the floating <ThemeToggle /> via a portal to document.body so
 *      it lives outside whatever container the page happens to have.
 */
export function ThemeProvider() {
  const [container, setContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    applyTheme(loadThemePreference());
    setContainer(document.body);
  }, []);

  if (!container) return null;
  return createPortal(<ThemeToggle />, container);
}
