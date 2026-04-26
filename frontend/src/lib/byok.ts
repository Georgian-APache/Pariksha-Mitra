"use client";

import { useEffect, useState } from "react";

const KEY_GEMINI = "pm.gemini_key";
const KEY_GROQ = "pm.groq_key";
const KEY_USER = "pm.user_id";

export type ApiKeyState = {
  gemini: string;
  groq: string;
  userId: string;
};

export function loadKeys(): ApiKeyState {
  if (typeof window === "undefined") return { gemini: "", groq: "", userId: "" };
  return {
    gemini: window.localStorage.getItem(KEY_GEMINI) ?? "",
    groq: window.localStorage.getItem(KEY_GROQ) ?? "",
    userId: window.localStorage.getItem(KEY_USER) ?? "",
  };
}

export function saveKeys(next: Partial<ApiKeyState>): ApiKeyState {
  const cur = loadKeys();
  const merged = { ...cur, ...next };
  if (typeof window !== "undefined") {
    if (next.gemini !== undefined) window.localStorage.setItem(KEY_GEMINI, merged.gemini);
    if (next.groq !== undefined) window.localStorage.setItem(KEY_GROQ, merged.groq);
    if (next.userId !== undefined) window.localStorage.setItem(KEY_USER, merged.userId);
    window.dispatchEvent(new CustomEvent("pm:keys-updated", { detail: merged }));
  }
  return merged;
}

export function clearKeys() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY_GEMINI);
  window.localStorage.removeItem(KEY_GROQ);
  window.localStorage.removeItem(KEY_USER);
  window.dispatchEvent(new CustomEvent("pm:keys-updated"));
}

export function useApiKeys(): [ApiKeyState, (next: Partial<ApiKeyState>) => void] {
  const [state, setState] = useState<ApiKeyState>({ gemini: "", groq: "", userId: "" });

  useEffect(() => {
    setState(loadKeys());
    const handler = () => setState(loadKeys());
    window.addEventListener("pm:keys-updated", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("pm:keys-updated", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const update = (next: Partial<ApiKeyState>) => {
    setState((s) => ({ ...s, ...next }));
    saveKeys(next);
  };
  return [state, update];
}
