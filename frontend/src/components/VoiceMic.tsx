"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Mic, MicOff, Volume2, VolumeX, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";
import { cn } from "@/lib/cn";
import {
  cancelSpeech,
  isVoiceSupported,
  speak,
  startRecognition,
  VOICE_LANG_LABEL,
  type VoiceLang,
} from "@/lib/voice";

type VoiceAskResponse = {
  answer_text: string;
  concept_id: string | null;
  sources: string[];
};

type Status = "idle" | "listening" | "thinking" | "speaking" | "error";

export function VoiceMic() {
  const [keys] = useApiKeys();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [lang, setLang] = useState<VoiceLang>("en-IN");
  const [transcript, setTranscript] = useState("");
  const [answer, setAnswer] = useState("");
  const [conceptId, setConceptId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(true);
  const recRef = useRef<{ stop: () => void } | null>(null);

  useEffect(() => {
    setSupported(isVoiceSupported());
  }, []);

  useEffect(() => {
    return () => {
      recRef.current?.stop();
      cancelSpeech();
    };
  }, []);

  function reset() {
    setTranscript("");
    setAnswer("");
    setConceptId(null);
    setError(null);
    setStatus("idle");
  }

  function startListening() {
    if (!supported) return;
    if (!keys.userId) {
      setError("Run the diagnostic first to start a session.");
      setStatus("error");
      return;
    }
    if (!keys.gemini) {
      setError("Add your free Gemini key first (top-right key button).");
      setStatus("error");
      return;
    }
    reset();
    setStatus("listening");
    recRef.current = startRecognition(lang, {
      onPartial: (t) => setTranscript(t),
      onFinal: (t) => {
        setTranscript(t);
        void ask(t);
      },
      onError: (msg) => {
        setError(msg);
        setStatus("error");
      },
      onEnd: () => {
        recRef.current = null;
      },
    });
  }

  function stopListening() {
    recRef.current?.stop();
    recRef.current = null;
    if (status === "listening") setStatus("idle");
  }

  async function ask(text: string) {
    setStatus("thinking");
    try {
      const res = await api<VoiceAskResponse>("/voice/ask", {
        method: "POST",
        body: { user_id: keys.userId, transcript: text, language: lang },
      });
      setAnswer(res.answer_text);
      setConceptId(res.concept_id);
      setStatus("speaking");
      speak(res.answer_text, lang, {
        onEnd: () => setStatus((s) => (s === "speaking" ? "idle" : s)),
      });
    } catch (err) {
      setError((err as Error).message);
      setStatus("error");
    }
  }

  function stopSpeaking() {
    cancelSpeech();
    setStatus("idle");
  }

  const listening = status === "listening";

  return (
    <>
      <motion.button
        type="button"
        aria-label="Open voice tutor"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-6 right-6 z-40 grid place-items-center size-14 rounded-full",
          "bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/30",
          "hover:shadow-xl hover:shadow-primary/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Mic className="size-6" />
        {listening && (
          <span className="absolute inset-0 rounded-full ring-2 ring-accent/70 animate-ping" />
        )}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ duration: 0.18 }}
            className="fixed bottom-24 right-6 z-40 w-[min(92vw,360px)] rounded-xl border border-border bg-card/90 backdrop-blur-md shadow-2xl"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="grid place-items-center size-7 rounded-md bg-gradient-to-br from-primary to-accent text-white">
                  <Mic className="size-4" />
                </span>
                <span className="text-sm font-medium">Voice tutor</span>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => {
                  stopListening();
                  cancelSpeech();
                  setOpen(false);
                  setStatus("idle");
                }}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Language</span>
                <div className="flex rounded-md border border-border overflow-hidden text-xs">
                  {(Object.keys(VOICE_LANG_LABEL) as VoiceLang[]).map((l) => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => setLang(l)}
                      className={cn(
                        "px-2.5 py-1 transition",
                        l === lang
                          ? "bg-primary/20 text-primary"
                          : "text-muted-foreground hover:bg-input/40",
                      )}
                    >
                      {VOICE_LANG_LABEL[l]}
                    </button>
                  ))}
                </div>
              </div>

              {!supported && (
                <p className="text-xs text-warning">
                  Voice mode needs Chromium-based browsers (Chrome, Edge, Brave).
                </p>
              )}

              <div className="rounded-md border border-border bg-input/30 p-3 min-h-[64px] text-sm">
                {transcript ? (
                  <span className="text-foreground/90">{transcript}</span>
                ) : (
                  <span className="text-muted-foreground">
                    {listening ? "Listening..." : "Tap the mic and ask anything from your syllabus."}
                  </span>
                )}
              </div>

              {answer && (
                <div className="rounded-md border border-accent/30 bg-accent/5 p-3 text-sm">
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="accent">Tutor</Badge>
                    {status === "speaking" ? (
                      <button
                        type="button"
                        onClick={stopSpeaking}
                        className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                      >
                        <VolumeX className="size-3" /> Stop
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setStatus("speaking");
                          speak(answer, lang, {
                            onEnd: () =>
                              setStatus((s) => (s === "speaking" ? "idle" : s)),
                          });
                        }}
                        className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                      >
                        <Volume2 className="size-3" /> Replay
                      </button>
                    )}
                  </div>
                  <p className="text-foreground/90 leading-relaxed">{answer}</p>
                  {conceptId && (
                    <div className="mt-2">
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/quiz?concept=${encodeURIComponent(conceptId)}`}>
                          Drill {conceptId}
                        </Link>
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {error && (
                <p className="text-xs text-destructive">{error}</p>
              )}

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-muted-foreground">
                  {status === "thinking"
                    ? "Thinking..."
                    : status === "speaking"
                      ? "Speaking..."
                      : status === "listening"
                        ? "Listening..."
                        : "Idle"}
                </span>
                {!listening ? (
                  <Button
                    size="sm"
                    onClick={startListening}
                    disabled={!supported || status === "thinking"}
                  >
                    {status === "thinking" ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Mic className="size-4" />
                    )}
                    Ask
                  </Button>
                ) : (
                  <Button size="sm" variant="destructive" onClick={stopListening}>
                    <MicOff className="size-4" /> Stop
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
