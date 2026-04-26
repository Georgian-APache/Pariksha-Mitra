"use client";

import Link from "next/link";
import { useState } from "react";
import { KeyRound, Brain } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { KeyModal } from "@/components/KeyModal";
import { StreakHud } from "@/components/StreakHud";
import { useApiKeys } from "@/lib/byok";

export function Header() {
  const [keys] = useApiKeys();
  const [open, setOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-border bg-background/70 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 h-14 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 group">
            <span className="grid place-items-center size-8 rounded-md bg-gradient-to-br from-primary to-accent text-white shadow-md">
              <Brain className="size-4" />
            </span>
            <span className="font-semibold tracking-tight">ParikshaMitra</span>
            <Badge variant="outline" className="hidden sm:inline-flex ml-1">
              Agentic
            </Badge>
          </Link>

          <nav className="hidden md:flex items-center gap-1 ml-4 text-sm text-muted-foreground">
            <Link href="/dashboard" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Dashboard</Link>
            <Link href="/quiz" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Quiz</Link>
            <Link href="/plan" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Plan</Link>
            <Link href="/graph" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Concept Graph</Link>
            <Link href="/doubt" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Snap-a-Doubt</Link>
            <Link href="/library" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Library</Link>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <StreakHud />
            <Button
              variant={keys.gemini ? "outline" : "default"}
              size="sm"
              onClick={() => setOpen(true)}
              title="API keys"
            >
              <KeyRound className="size-4" />
              <span className="hidden sm:inline">{keys.gemini ? "Keys set" : "Add key"}</span>
            </Button>
          </div>
        </div>
      </header>
      <KeyModal open={open} onOpenChange={setOpen} />
    </>
  );
}
