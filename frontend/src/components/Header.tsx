"use client";

import Link from "next/link";
import { Brain } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { StreakHud } from "@/components/StreakHud";
import { TeamCredit } from "@/components/TeamCredit";

export function Header() {
  return (
    <>
      <header className="sticky top-0 z-30 border-b border-border bg-background/70 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 h-14 flex items-center gap-4">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 shrink">
            <Link href="/" className="flex items-center gap-2 group shrink-0">
              <span className="grid place-items-center size-8 rounded-md bg-gradient-to-br from-primary to-accent text-white shadow-md">
                <Brain className="size-4" />
              </span>
              <span className="font-semibold tracking-tight">ParikshaMitra</span>
              <Badge variant="outline" className="hidden sm:inline-flex ml-1">
                Agentic
              </Badge>
            </Link>
            <TeamCredit variant="header" />
          </div>

          <nav className="hidden md:flex items-center gap-1 ml-4 text-sm text-muted-foreground">
            <Link href="/dashboard" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Dashboard</Link>
            <Link href="/quiz" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Quiz</Link>
            <Link href="/graph" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Concept Graph</Link>
            <Link href="/doubt" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Snap-a-Doubt</Link>
            <Link href="/library" className="px-3 py-1.5 rounded hover:text-foreground hover:bg-input/40">Library</Link>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <StreakHud />
          </div>
        </div>
      </header>
    </>
  );
}
