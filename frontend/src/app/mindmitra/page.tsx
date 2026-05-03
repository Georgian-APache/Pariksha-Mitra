"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Brain, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";
import { MoodCheckin } from "@/components/MoodCheckin";
import { TherapistChat } from "@/components/TherapistChat";
import { CopingCard } from "@/components/CopingCard";
import { MoodChart } from "@/components/MoodChart";
import { api } from "@/lib/api";
import { loadKeys } from "@/lib/byok";
import type { CheckinResponse, ChatResponse, MoodHistory } from "@/lib/types";

type ChatMessage = { role: "user" | "assistant"; content_en: string; content_hi?: string };

export default function MindMitraPage() {
  const userId = loadKeys().userId;
  const [tab, setTab] = useState<"checkin" | "chat">("checkin");
  const [loading, setLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<CheckinResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content_en: "Hi! I'm MindMitra 🧠 — your companion through JEE prep. How are you feeling today?",
      content_hi: "नमस्ते! मैं MindMitra हूँ 🧠 — JEE की तैयारी में आपका साथी। आज कैसा महसूस हो रहा है?",
    },
  ]);
  const [convId, setConvId] = useState("");
  const [moodHistory, setMoodHistory] = useState<MoodHistory | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (!userId) return;
    api<MoodHistory>(`/mental-health/${userId}/history`).then(setMoodHistory).catch(() => null);
  }, [userId]);

  async function handleCheckin(score: number, tags: string[], note: string) {
    if (!userId) { toast.error("Please complete onboarding first."); return; }
    setLoading(true);
    try {
      const res = await api<CheckinResponse>("/mental-health/checkin", {
        method: "POST",
        body: { user_id: userId, mood_score: score, feeling_text: note, tags },
      });
      setLastResponse(res);
      // refresh history
      const h = await api<MoodHistory>(`/mental-health/${userId}/history`);
      setMoodHistory(h);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleChat(text: string) {
    if (!userId) { toast.error("Please complete onboarding first."); return; }
    setMessages((prev) => [...prev, { role: "user", content_en: text }]);
    setLoading(true);
    try {
      const res = await api<ChatResponse>("/mental-health/chat", {
        method: "POST",
        body: { user_id: userId, message: text, conversation_id: convId },
      });
      if (!convId) setConvId(res.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content_en: res.response_en, content_hi: res.response_hi },
      ]);
      if (res.parent_alerted) {
        toast.success("Your parents have been notified via WhatsApp.", { duration: 8000 });
      } else if (res.escalation_needed) {
        toast.warning("Crisis detected. No parent contact on file — please add one in onboarding.", { duration: 10000 });
      }
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen"
      style={{ background: "linear-gradient(135deg, oklch(0.97 0.01 280), oklch(0.95 0.02 200))" }}
    >
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3"
        >
          <div className="size-12 rounded-2xl bg-[oklch(0.65_0.15_290)]/15 flex items-center justify-center">
            <Brain className="size-6 text-[oklch(0.65_0.15_290)]" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">MindMitra</h1>
            <p className="text-sm text-muted-foreground">Your JEE mental wellness companion</p>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 p-1 rounded-xl bg-[oklch(0.65_0.15_290)]/8 w-fit">
          {(["checkin", "chat"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                tab === t
                  ? "bg-[oklch(0.65_0.15_290)] text-white shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "checkin" ? "Mood Check-in" : "Chat"}
            </button>
          ))}
        </div>

        {/* Main card */}
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-[oklch(0.65_0.15_290)]/20 bg-background/80 backdrop-blur p-6 shadow-sm"
        >
          {tab === "checkin" ? (
            <div className="space-y-4">
              <MoodCheckin onSubmit={handleCheckin} loading={loading} />
              {lastResponse && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3 pt-2 border-t border-border">
                  <div className="space-y-1">
                    <p className="text-sm leading-relaxed">{lastResponse.response_en}</p>
                    <p className="text-xs text-muted-foreground italic">{lastResponse.response_hi}</p>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {lastResponse.mood_tags.map((tag) => (
                      <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-[oklch(0.72_0.12_200)]/15 text-[oklch(0.45_0.12_200)]">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <CopingCard suggestion={lastResponse.coping_suggestion} followUp={lastResponse.follow_up_question} />
                  {lastResponse.escalation_needed && (
                    <div className="rounded-lg bg-[oklch(0.65_0.18_25)]/10 border border-[oklch(0.65_0.18_25)]/30 px-4 py-3 text-sm text-[oklch(0.5_0.18_25)]">
                      💛 It seems like you've been having a tough time. Please consider talking to a counsellor or a trusted adult.
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          ) : (
            <div className="h-[460px] flex flex-col">
              <TherapistChat messages={messages} onSend={handleChat} loading={loading} />
            </div>
          )}
        </motion.div>

        {/* Mood history drawer */}
        {moodHistory && moodHistory.mood_history.length > 0 && (
          <div className="rounded-2xl border border-border bg-background/70 overflow-hidden">
            <button
              type="button"
              onClick={() => setHistoryOpen((p) => !p)}
              className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium"
            >
              <span>Mood history (last 14 days)</span>
              {historyOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>
            {historyOpen && (
              <div className="px-5 pb-5">
                <MoodChart history={moodHistory.mood_history} />
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-center text-muted-foreground">
          MindMitra is not a substitute for professional mental health support.
          If you are in crisis, please contact iCall: 9152987821.
        </p>
      </div>
    </div>
  );
}
