const envUrl =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL?.trim()
    ? process.env.NEXT_PUBLIC_API_URL.trim().replace(/\/$/, "")
    : "";

const DEFAULT_JSON_TIMEOUT_MS = 90_000;
const DEFAULT_UPLOAD_TIMEOUT_MS = 180_000;
const MAX_RETRIES = 3;

/**
 * Public API origin with no trailing slash.
 * Empty string = use same-origin `/pm-api` rewrite to the FastAPI backend (see `next.config.ts`).
 */
export const API_URL = envUrl;

function requestUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (envUrl) return `${envUrl}${p}`;
  return `/pm-api${p}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetriableNetworkError(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  if (e instanceof DOMException && e.name === "AbortError") return false;
  return false;
}

/** User-safe message; never forwards stack traces or huge HTML bodies to UI. */
export function sanitizeClientErrorMessage(raw: string, maxLen = 400): string {
  const t = raw.replace(/\s+/g, " ").trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen)}…`;
}

function withTimeoutSignal(
  userSignal: AbortSignal | undefined,
  timeoutMs: number,
): AbortSignal | undefined {
  if (typeof AbortSignal === "undefined" || !("timeout" in AbortSignal)) {
    return userSignal;
  }
  const timed = AbortSignal.timeout(timeoutMs);
  if (!userSignal) return timed;
  if ("any" in AbortSignal && typeof AbortSignal.any === "function") {
    return AbortSignal.any([userSignal, timed]);
  }
  return userSignal;
}

async function fetchWithRetry(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const signal = withTimeoutSignal(init.signal as AbortSignal | undefined, timeoutMs);
    try {
      const res = await fetch(url, { ...init, signal });
      return res;
    } catch (e) {
      lastError = e;
      const retriable = isRetriableNetworkError(e);
      if (!retriable || attempt === MAX_RETRIES - 1) {
        break;
      }
      await sleep(300 * 2 ** attempt);
    }
  }
  throw lastError;
}

export type ApiInit = Omit<RequestInit, "body" | "headers"> & {
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Override default JSON request timeout (ms). */
  timeoutMs?: number;
};

/** API calls use the server-configured Gemini key (no client key entry). */
export async function api<T = unknown>(path: string, init: ApiInit = {}): Promise<T> {
  const { timeoutMs = DEFAULT_JSON_TIMEOUT_MS, ...rest } = init;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(rest.headers ?? {}),
  };

  const url = requestUrl(path);
  let res: Response;
  try {
    res = await fetchWithRetry(
      url,
      {
        ...rest,
        headers,
        body: rest.body !== undefined ? JSON.stringify(rest.body) : undefined,
      },
      timeoutMs,
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Network error";
    const hint = envUrl
      ? `Could not reach ${envUrl}. Start uvicorn on that host/port, or remove NEXT_PUBLIC_API_URL from .env.local to use the /pm-api dev proxy.`
      : `Could not reach API via ${url}. Start the backend (uvicorn), or set BACKEND_DEV_PROXY_URL in .env.local.`;
    throw new Error(sanitizeClientErrorMessage(`${msg} - ${hint}`));
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let detail = text;
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      /* ignore */
    }
    throw new Error(sanitizeClientErrorMessage(detail || `${res.status} ${res.statusText}`));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function uploadForm<T = unknown>(
  path: string,
  form: FormData,
  init: Omit<ApiInit, "body"> = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_UPLOAD_TIMEOUT_MS, ...rest } = init;
  const headers: Record<string, string> = { ...(rest.headers ?? {}) };
  const url = requestUrl(path);
  let res: Response;
  try {
    res = await fetchWithRetry(
      url,
      {
        ...rest,
        headers,
        method: rest.method ?? "POST",
        body: form,
      },
      timeoutMs,
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Network error";
    const hint = envUrl ? `Could not reach ${envUrl}.` : `Could not reach API via ${url}. Is uvicorn running?`;
    throw new Error(sanitizeClientErrorMessage(`${msg} - ${hint}`));
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(sanitizeClientErrorMessage(text || `${res.status} ${res.statusText}`));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Absolute or same-origin URL for SSE / downloads (no path prefix). */
export function absoluteApiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (typeof window !== "undefined") {
    if (envUrl) return `${envUrl}${p}`;
    return `${window.location.origin}/pm-api${p}`;
  }
  if (envUrl) return `${envUrl}${p}`;
  return `http://127.0.0.1:8000${p}`;
}
