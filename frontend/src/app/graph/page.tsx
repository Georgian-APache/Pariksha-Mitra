"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Loader2, Network, Sparkles, Target } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";

const ConceptGraph = dynamic(
  () => import("@/components/ConceptGraph").then((m) => m.ConceptGraph),
  { ssr: false, loading: () => <div className="h-[60vh] grid place-items-center text-muted-foreground"><Loader2 className="size-5 animate-spin" /></div> },
);

type GraphResponse = {
  exam: string;
  subjects: Record<string, number>;
  nodes: { data: { id: string; label: string; subject: string; weight: number } }[];
  edges: { data: { id: string; source: string; target: string } }[];
  mastery: Record<string, number>;
  sm2: Record<string, { interval_days: number; due: string; last_score: number }>;
};

export default function GraphPage() {
  const [keys] = useApiKeys();
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<{ id: string; label: string } | null>(null);

  useEffect(() => {
    if (!keys.userId) {
      setLoading(false);
      return;
    }
    api<GraphResponse>(`/graph/${keys.userId}`)
      .then(setData)
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [keys.userId]);

  if (!keys.userId) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center space-y-3">
        <Network className="size-8 text-accent mx-auto" />
        <p className="text-muted-foreground">Run the diagnostic first to populate your knowledge graph.</p>
        <Button asChild><Link href="/onboarding">Start diagnostic</Link></Button>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-12">
        <Loader2 className="size-4 animate-spin" /> Building your concept graph...
      </div>
    );
  }

  const sumNodes = data.nodes.length;
  const knownConcepts = Object.values(data.mastery).filter((m) => m > 0).length;

  return (
    <div className="space-y-4 py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Network className="size-5 text-accent" />
            Concept dependency graph
          </h1>
          <p className="text-sm text-muted-foreground">
            {sumNodes} concepts {" | "} {knownConcepts} touched {" | "} click any node to drill into 5 questions on it.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{data.exam.replace("_", " ")}</Badge>
          {Object.entries(data.subjects).map(([s, w]) => (
            <Badge key={s} variant="default">{s} {Math.round(w * 100)}%</Badge>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-4">
        <Card>
          <CardContent className="p-3">
            <ConceptGraph
              nodes={data.nodes}
              edges={data.edges}
              mastery={data.mastery}
              onSelect={(id, label) => setSelected({ id, label })}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-accent" />
              {selected ? selected.label : "Select a concept"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {selected ? (
              <>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-0.5">
                    Concept ID
                  </div>
                  <code className="text-xs">{selected.id}</code>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-0.5">
                    Mastery
                  </div>
                  <div className="font-medium">
                    {Math.round((data.mastery[selected.id] ?? 0) * 100)}%
                  </div>
                </div>
                {data.sm2[selected.id] && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground mb-0.5">
                      Spaced repetition
                    </div>
                    <div>
                      Next review: <span className="font-medium">{data.sm2[selected.id].due}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Interval: {data.sm2[selected.id].interval_days}d {" | "} Last score: {Math.round((data.sm2[selected.id].last_score ?? 0) * 100)}%
                    </div>
                  </div>
                )}
                <Button asChild className="w-full">
                  <Link href={`/quiz?concept=${encodeURIComponent(selected.id)}`}>
                    <Target className="size-4" /> Drill 5 questions
                  </Link>
                </Button>
              </>
            ) : (
              <p className="text-muted-foreground">
                Click any node in the graph. Red = weak, amber = ok, green = strong.
                Edges represent prerequisite chains - the Analyst walks them to detect
                root-cause gaps.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
