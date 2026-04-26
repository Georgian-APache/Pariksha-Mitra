import { loadKeys } from "./byok";

export const API_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export type ApiInit = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

export async function api<T = unknown>(path: string, init: ApiInit = {}): Promise<T> {
  const keys = loadKeys();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers ?? {}),
  };
  if (keys.gemini) headers["X-Gemini-Key"] = keys.gemini;
  if (keys.groq) headers["X-Groq-Key"] = keys.groq;

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.detail ?? text;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function uploadForm<T = unknown>(
  path: string,
  form: FormData,
  init: Omit<ApiInit, "body"> = {},
): Promise<T> {
  const keys = loadKeys();
  const headers: Record<string, string> = { ...(init.headers ?? {}) };
  if (keys.gemini) headers["X-Gemini-Key"] = keys.gemini;
  if (keys.groq) headers["X-Groq-Key"] = keys.groq;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    method: init.method ?? "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
