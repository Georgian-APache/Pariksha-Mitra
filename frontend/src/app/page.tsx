"use client";

import Link from "next/link";
import {
  Brain,
  Compass,
  Camera,
  Network,
  Mic,
  TrendingUp,
  Sparkles,
  Activity,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { TeamCredit } from "@/components/TeamCredit";

const surprises = [
  {
    icon: Activity,
    title: "Live agent reasoning trace",
    desc: "Watch Planner -> Analyst -> Companion think in real-time over SSE.",
  },
  {
    icon: Camera,
    title: "Snap-a-Doubt",
    desc: "Photograph any handwritten problem - Gemini Vision solves it and tags the weak concept.",
  },
  {
    icon: Network,
    title: "Interactive Concept Graph",
    desc: "Cytoscape view of your knowledge graph with mastery heatmap and click-to-drill quizzes.",
  },
  {
    icon: TrendingUp,
    title: "Predictive rank simulator",
    desc: "Monte-Carlo extrapolation of your trajectory: percentile + 90% CI by exam day.",
  },
  {
    icon: Mic,
    title: "Voice mode",
    desc: "Hindi + English speech in / speech out via Web Speech API. Zero cost.",
  },
  {
    icon: Sparkles,
    title: "PDF-RAG over NCERT",
    desc: "Upload a chapter, get grounded MCQs with source citations.",
  },
];

export default function Home() {
  return (
    <div className="space-y-12 py-6">
      <section className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
        <div className="space-y-6">
          <Badge variant="outline" className="text-xs">
            An AI that studies you, so you can study smarter
          </Badge>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05]">
            ParikshaMitra
            <span className="block text-2xl sm:text-3xl lg:text-4xl mt-2 bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              {`\u092A\u0930\u0940\u0915\u094D\u0937\u093E \u092E\u093F\u0924\u094D\u0930`}
            </span>
          </h1>
          <TeamCredit variant="hero" />
          <p className="text-lg text-muted-foreground max-w-xl">
            An agentic AI study companion for JEE, NEET and other Indian competitive
            exams. A 4+1 LangGraph cognitive architecture - Orchestrator, Planner,
            QuizMaster, Analyst, Companion - autonomously plans, tests, analyses and
            adapts your preparation. Every day. In Hindi or English.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/onboarding">Start free diagnostic</Link>
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            <Badge variant="default">LangGraph 4+1</Badge>
            <Badge variant="accent">Gemini 2.0 / 2.5 Flash</Badge>
            <Badge variant="success">Server-hosted AI</Badge>
            <Badge variant="warning">SM-2 + CAT-lite</Badge>
          </div>
        </div>

        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="bg-gradient-to-br from-primary/30 via-accent/20 to-transparent p-6 space-y-5">
              <div className="flex items-center gap-3 text-sm text-foreground/80">
                <Brain className="size-4 text-accent" />
                <span>4+1 cognitive architecture</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { name: "Planner", role: "allocates daily hours" },
                  { name: "QuizMaster", role: "adaptive CAT-lite" },
                  { name: "Analyst", role: "readiness + gaps" },
                  { name: "Companion", role: "bilingual nudges" },
                ].map((a) => (
                  <div key={a.name} className="rounded-lg border border-border/60 p-3 bg-background/40">
                    <div className="text-sm font-medium">{a.name}</div>
                    <div className="text-xs text-muted-foreground">{a.role}</div>
                  </div>
                ))}
              </div>
              <div className="rounded-lg border border-accent/30 bg-accent/10 p-4 text-sm">
                <div className="flex items-center gap-2 font-medium mb-1">
                  <Compass className="size-4 text-accent" /> Orchestrator
                </div>
                <p className="text-muted-foreground">
                  Manages global state in a persistent Student Knowledge Graph and routes
                  data between specialised agents.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <div className="flex items-end justify-between mb-4">
          <h2 className="text-2xl font-semibold tracking-tight">Beyond the deck</h2>
          <span className="text-sm text-muted-foreground">10 surprises shipped</span>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {surprises.map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="hover:border-primary/40 transition">
              <CardContent className="p-5 space-y-2">
                <div className="size-9 grid place-items-center rounded-md bg-primary/15 text-primary">
                  <Icon className="size-4" />
                </div>
                <div className="font-medium">{title}</div>
                <div className="text-sm text-muted-foreground">{desc}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
