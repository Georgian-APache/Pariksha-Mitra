"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import { Brain } from "lucide-react";

if (typeof window !== "undefined" && !(cytoscape as { _fcose?: boolean })._fcose) {
  cytoscape.use(fcose);
  (cytoscape as { _fcose?: boolean })._fcose = true;
}

type NodeData = {
  id: string;
  label: string;
  subject: string;
  weight: number;
};
type EdgeData = { id: string; source: string; target: string };

export function ConceptGraph({
  nodes,
  edges,
  mastery,
  onSelect,
}: {
  nodes: { data: NodeData }[];
  edges: { data: EdgeData }[];
  mastery: Record<string, number>;
  onSelect?: (nodeId: string, label: string) => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [activeSubject, setActiveSubject] = useState<string | null>(null);

  const subjects = useMemo(
    () => Array.from(new Set(nodes.map((n) => n.data.subject))),
    [nodes],
  );

  useEffect(() => {
    if (!ref.current || cyRef.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...nodes.map((n) => ({
          data: {
            ...n.data,
            mastery: mastery[n.data.id] ?? 0,
          },
        })),
        ...edges.map((e) => ({ data: e.data })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#fff",
            "font-size": 8,
            "text-wrap": "wrap",
            "text-max-width": "70px",
            "text-valign": "center",
            "text-halign": "center",
            "text-outline-color": "#1d1f2e",
            "text-outline-width": 1,
            width: "mapData(weight, 0, 0.08, 22, 60)",
            height: "mapData(weight, 0, 0.08, 22, 60)",
            "border-width": 1.5,
            "border-color": "rgba(255,255,255,0.18)",
          },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            width: 1,
            "line-color": "rgba(160, 170, 220, 0.18)",
            "target-arrow-color": "rgba(160, 170, 220, 0.45)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#7eddff",
            "border-width": 3,
          },
        },
      ],
      layout: {
        name: "fcose",
        quality: "default",
        animate: false,
        nodeRepulsion: 5500,
        idealEdgeLength: 75,
        nodeSeparation: 60,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.2,
      minZoom: 0.4,
      maxZoom: 2.2,
    });

    // Compute and assign colour per node based on mastery
    cy.nodes().forEach((n) => {
      const m = (n.data("mastery") as number) || 0;
      n.data("color", masteryToColor(m));
    });

    cy.on("tap", "node", (evt) => {
      const n = evt.target;
      onSelect?.(n.id(), n.data("label"));
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update mastery colours when prop changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().forEach((n) => {
      const m = mastery[n.id()] ?? 0;
      n.data("mastery", m);
      n.data("color", masteryToColor(m));
    });
  }, [mastery]);

  // Highlight subject
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().forEach((n) => {
      if (!activeSubject) {
        n.style("opacity", 1);
      } else {
        n.style("opacity", n.data("subject") === activeSubject ? 1 : 0.18);
      }
    });
    cy.edges().forEach((e) => {
      if (!activeSubject) {
        e.style("opacity", 1);
      } else {
        const src = cy.getElementById(e.data("source")).data("subject");
        const tgt = cy.getElementById(e.data("target")).data("subject");
        e.style("opacity", src === activeSubject || tgt === activeSubject ? 1 : 0.1);
      }
    });
  }, [activeSubject]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-muted-foreground inline-flex items-center gap-1">
          <Brain className="size-3" /> Subjects:
        </span>
        <button
          onClick={() => setActiveSubject(null)}
          className={`text-xs px-2.5 py-1 rounded-full border ${
            activeSubject === null
              ? "border-primary bg-primary/15 text-primary"
              : "border-border hover:bg-input/40"
          }`}
        >
          All
        </button>
        {subjects.map((s) => (
          <button
            key={s}
            onClick={() => setActiveSubject(s)}
            className={`text-xs px-2.5 py-1 rounded-full border ${
              activeSubject === s
                ? "border-accent bg-accent/15 text-accent"
                : "border-border hover:bg-input/40"
            }`}
          >
            {s}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground inline-flex items-center gap-2">
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-[oklch(0.62_0.22_25)]" /> weak
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-[oklch(0.78_0.18_80)]" /> ok
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-[oklch(0.7_0.18_150)]" /> strong
          </span>
        </span>
      </div>
      <div
        ref={ref}
        className="w-full h-[60vh] rounded-lg border border-border bg-background/30"
      />
    </div>
  );
}

function masteryToColor(m: number): string {
  // 0 -> red, 0.5 -> amber, 1 -> green
  const clamped = Math.max(0, Math.min(1, m));
  // OKLCH hues: 25 (red), 80 (amber), 150 (green)
  const hue = clamped < 0.5 ? 25 + clamped * 2 * (80 - 25) : 80 + (clamped - 0.5) * 2 * (150 - 80);
  const lightness = 0.55 + clamped * 0.2;
  return `oklch(${lightness.toFixed(2)} 0.18 ${Math.round(hue)})`;
}
