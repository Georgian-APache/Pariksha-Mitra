"use client";

/**
 * Thin helpers around the browser Web Speech API.
 *
 * STT: SpeechRecognition / webkitSpeechRecognition (Chromium, Safari, Edge).
 * TTS: window.speechSynthesis.
 *
 * We keep the surface minimal so the VoiceMic component owns presentation.
 */

export type VoiceLang = "en-IN" | "hi-IN";

export const VOICE_LANG_LABEL: Record<VoiceLang, string> = {
  "en-IN": "English",
  "hi-IN": "Hindi",
};

// SpeechRecognition is not in the default lib.dom types. Define just enough.
type SpeechRecognitionResultLike = {
  isFinal: boolean;
  0: { transcript: string; confidence?: number };
};

type SpeechRecognitionEventLike = Event & {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
};

export type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: ((ev: Event) => void) | null;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: Event & { error?: string }) => void) | null;
  onend: ((ev: Event) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isVoiceSupported(): boolean {
  if (typeof window === "undefined") return false;
  return !!getRecognitionCtor() && !!window.speechSynthesis;
}

export type RecognizeHandlers = {
  onPartial?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (msg: string) => void;
  onEnd?: () => void;
};

/**
 * Start a single dictation pass. Returns a controller with `stop()`.
 * The recognition stops automatically when the user finishes speaking.
 */
export function startRecognition(
  lang: VoiceLang,
  handlers: RecognizeHandlers,
): { stop: () => void } | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) {
    handlers.onError?.("Speech recognition is not supported in this browser");
    return null;
  }
  const rec = new Ctor();
  rec.lang = lang;
  rec.continuous = false;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  let finalText = "";
  rec.onresult = (ev) => {
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i];
      const t = r[0]?.transcript ?? "";
      if (r.isFinal) finalText += t;
      else interim += t;
    }
    handlers.onPartial?.(finalText + interim);
  };
  rec.onerror = (ev) => {
    handlers.onError?.(ev.error ?? "recognition error");
  };
  rec.onend = () => {
    if (finalText.trim()) handlers.onFinal?.(finalText.trim());
    handlers.onEnd?.();
  };

  try {
    rec.start();
  } catch (err) {
    handlers.onError?.((err as Error).message);
    return null;
  }
  return { stop: () => rec.stop() };
}

/**
 * Speak `text` via SpeechSynthesis. Cancels any in-flight speech first so
 * back-to-back questions don't queue up indefinitely.
 */
export function speak(
  text: string,
  lang: VoiceLang,
  opts: { rate?: number; pitch?: number; onEnd?: () => void } = {},
): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const synth = window.speechSynthesis;
  synth.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang;
  utter.rate = opts.rate ?? 1;
  utter.pitch = opts.pitch ?? 1;
  const voices = synth.getVoices();
  const match = voices.find((v) => v.lang === lang) ?? voices.find((v) => v.lang.startsWith(lang.slice(0, 2)));
  if (match) utter.voice = match;
  if (opts.onEnd) utter.onend = () => opts.onEnd?.();
  synth.speak(utter);
}

export function cancelSpeech(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
}
