"use client";

import { useEffect, useState } from "react";

const KEY_USER = "pm.user_id";

export type ApiKeyState = {
  userId: string;
};

/** In-memory fallback when localStorage is unavailable (private mode, quota, policy). */
let memoryUserId = "";

export function loadKeys(): ApiKeyState {
  if (typeof window === "undefined") {
    return { userId: memoryUserId };
  }
  try {
    const u = window.localStorage.getItem(KEY_USER) ?? "";
    memoryUserId = u;
    return { userId: u };
  } catch {
    return { userId: memoryUserId };
  }
}

export function saveKeys(next: Partial<ApiKeyState>): ApiKeyState {
  const cur = loadKeys();
  const merged = { ...cur, ...next };
  if (typeof window !== "undefined") {
    try {
      if (next.userId !== undefined) {
        window.localStorage.setItem(KEY_USER, merged.userId);
      }
    } catch {
      /* ignore quota / disabled storage */
    }
    memoryUserId = merged.userId;
    try {
      window.dispatchEvent(new CustomEvent("pm:keys-updated", { detail: merged }));
    } catch {
      /* ignore */
    }
  } else {
    if (next.userId !== undefined) memoryUserId = merged.userId;
  }
  return merged;
}

export function clearKeys() {
  memoryUserId = "";
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY_USER);
  } catch {
    /* ignore */
  }
  try {
    window.dispatchEvent(new CustomEvent("pm:keys-updated"));
  } catch {
    /* ignore */
  }
}

export function useApiKeys(): [ApiKeyState, (next: Partial<ApiKeyState>) => void] {
  const [state, setState] = useState<ApiKeyState>({ userId: "" });

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
