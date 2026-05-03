"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Brain } from "lucide-react";

type Message = {
  role: "user" | "assistant";
  content_en: string;
  content_hi?: string;
};

type Props = {
  messages: Message[];
  onSend: (text: string) => void;
  loading?: boolean;
};

export function TherapistChat({ messages, onSend, loading }: Props) {
  const [input, setInput] = useState("");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const t = input.trim();
    if (!t || loading) return;
    setInput("");
    onSend(t);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Lang toggle */}
      <div className="flex gap-2 mb-3">
        {(["en", "hi"] as const).map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLang(l)}
            className={`px-3 py-1 rounded-full text-xs border transition ${
              lang === l
                ? "bg-[oklch(0.65_0.15_290)] text-white border-transparent"
                : "border-border hover:bg-input/30"
            }`}
          >
            {l === "en" ? "English" : "हिन्दी"}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: msg.role === "user" ? 20 : -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: 0.05 }}
              className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="size-7 rounded-full bg-[oklch(0.65_0.15_290)]/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Brain className="size-4 text-[oklch(0.65_0.15_290)]" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[oklch(0.65_0.15_290)] text-white rounded-tr-sm"
                    : "bg-[oklch(0.65_0.15_290)]/10 text-foreground rounded-tl-sm"
                }`}
              >
                {msg.role === "assistant" && lang === "hi" && msg.content_hi
                  ? msg.content_hi
                  : msg.content_en}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-muted-foreground text-sm"
          >
            <Brain className="size-4 text-[oklch(0.65_0.15_290)]" />
            <span className="animate-pulse">MindMitra is thinking…</span>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-border">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Share how you're feeling…"
          className="flex-1 rounded-xl border border-border bg-input/20 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[oklch(0.65_0.15_290)]"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="size-9 rounded-xl bg-[oklch(0.65_0.15_290)] disabled:opacity-40 flex items-center justify-center"
        >
          <Send className="size-4 text-white" />
        </button>
      </div>
    </div>
  );
}
