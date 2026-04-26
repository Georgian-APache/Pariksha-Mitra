"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, ImageIcon, Loader2, Sparkles, Upload } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { uploadForm } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";

type DoubtResponse = {
  subject: string;
  concept_id: string;
  concept_name: string;
  answer: string;
  steps: string[];
  confidence: number;
  follow_up: string;
  matched_concept: boolean;
  mastery_after: Record<string, number>;
};

export default function DoubtPage() {
  const [keys] = useApiKeys();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DoubtResponse | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function submit() {
    if (!keys.userId) {
      toast.error("Run the diagnostic first");
      return;
    }
    if (!file) {
      toast.error("Pick or capture an image first");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("user_id", keys.userId);
      fd.append("image", file);
      const res = await uploadForm<DoubtResponse>("/doubt", fd);
      setResult(res);
      toast.success("Solved + tagged into your knowledge graph");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-6 py-2">
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Camera className="size-5 text-accent" />
            Snap-a-Doubt
          </h1>
          <p className="text-sm text-muted-foreground">
            Photograph any handwritten or printed problem - Gemini Vision will
            solve it, identify the concept, and lift your mastery on that node.
          </p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-4">
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {preview ? (
              <div className="relative rounded-lg overflow-hidden border border-border bg-background/40">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="doubt" className="w-full max-h-[60vh] object-contain" />
              </div>
            ) : (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="w-full rounded-lg border border-dashed border-border bg-background/40 p-12 grid place-items-center text-muted-foreground hover:border-primary/40 hover:bg-input/40 transition"
              >
                <div className="flex flex-col items-center gap-2">
                  <ImageIcon className="size-8" />
                  <span className="text-sm">Tap to capture or choose an image</span>
                  <span className="text-xs">JPG / PNG / WebP - Gemini multimodal</span>
                </div>
              </button>
            )}

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => inputRef.current?.click()}>
                <Upload className="size-4" /> {file ? "Replace" : "Pick image"}
              </Button>
              <Button onClick={submit} disabled={!file || busy}>
                {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                Solve with Gemini Vision
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        {result ? (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Solution</CardTitle>
                  <Badge variant={result.matched_concept ? "success" : "warning"}>
                    {Math.round(result.confidence * 100)}% confidence
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{result.subject || "—"}</Badge>
                  <Badge variant="default">{result.concept_id}</Badge>
                  {result.matched_concept ? (
                    <Badge variant="success">+0.05 mastery</Badge>
                  ) : (
                    <Badge variant="warning">Concept unmatched</Badge>
                  )}
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                    Answer
                  </div>
                  <div className="font-medium">{result.answer}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                    Steps
                  </div>
                  <ol className="list-decimal pl-5 space-y-1.5">
                    {result.steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                </div>
                {result.follow_up && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                      Follow-up question
                    </div>
                    <div className="italic">{result.follow_up}</div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <Card>
            <CardContent className="p-12 text-center text-muted-foreground space-y-3">
              <Sparkles className="size-8 mx-auto text-accent" />
              <p>
                Ask a doubt. The agent will solve it, identify the concept and update
                your knowledge graph in one shot.
              </p>
              <p className="text-xs">
                Pro tip: well-lit, clearly written images work best. Hindi or
                English / mixed handwriting is fine.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
