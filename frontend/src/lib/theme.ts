"use client";

/**
 * Theme helpers - persist a "dark" | "light" | "system" preference in
 * localStorage and reflect it as a `data-theme` attribute on `<html>`.
 *
 * Dark is the visual default. The "system" mode follows
 * `prefers-color-scheme` and updates live.
 */

export const THEME_STORAGE_KEY = "pm.theme";

export type ThemePreference = "dark" | "light" | "system";
export type EffectiveTheme = "dark" | "light";

const VALID: readonly ThemePreference[] = ["dark", "light", "system"] as const;

export function loadThemePreference(): ThemePreference {
  if (typeof window === "undefined") return "dark";
  const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
  return (VALID as readonly string[]).includes(raw ?? "")
    ? (raw as ThemePreference)
    : "dark";
}

export function saveThemePreference(pref: ThemePreference): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(THEME_STORAGE_KEY, pref);
  window.dispatchEvent(
    new CustomEvent("pm:theme-updated", { detail: pref }),
  );
}

export function systemPrefersLight(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: light)").matches;
}

export function resolveEffectiveTheme(pref: ThemePreference): EffectiveTheme {
  if (pref === "system") return systemPrefersLight() ? "light" : "dark";
  return pref;
}

export function applyTheme(pref: ThemePreference): EffectiveTheme {
  if (typeof document === "undefined") return "dark";
  const effective = resolveEffectiveTheme(pref);
  document.documentElement.setAttribute("data-theme", effective);
  document.documentElement.style.colorScheme = effective;
  return effective;
}

export function nextThemePreference(cur: ThemePreference): ThemePreference {
  if (cur === "dark") return "light";
  if (cur === "light") return "system";
  return "dark";
}
