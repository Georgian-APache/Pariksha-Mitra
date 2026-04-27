"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  Library,
  Loader2,
  Sparkles,
  Upload,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, uploadForm } from "@/lib/api";
import { useApiKeys } from "@/lib/byok";

type Doc = {
  id: string;
  title: string;
  collection: string;
  pages: number;
  chunks: number;
  created_at: string;
};

type GroundedQuiz = {
  questions: {
    concept_id?: string;
    subject?: string;
    difficulty?: number;
    stem: string;
    options: string[];
    correct_index: number;
    explanation?: string;
  }[];
  citations: { index: number; page: number; preview: string }[];
};

export default function LibraryPage() {
  const [keys] = useApiKeys();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [topic, setTopic] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState<string | null>(null);
  const [quiz, setQuiz] = useState<GroundedQuiz | null>(null);
  const [activeCollection, setActiveCollection] = useState<string | null>(null);
  const [chosen, setChosen] = useState<Record<number, number>>({});
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function refresh(signal?: AbortSignal) {
    if (!keys.userId) return;
    setDocsError(null);
    try {
      const res = await api<{ documents: Doc[] }>(`/rag/docs/${keys.userId}`, { signal });
      if (signal?.aborted) return;
      setDocs(res.documents);
    } catch (err) {
      if ((err as Error)?.name === "AbortError" || signal?.aborted) return;
      const msg = (err as Error).message || "Could not load chapters";
      setDocsError(msg);
      toast.error(msg);
    }
  }

  useEffect(() => {
    const ctrl = new AbortController();
    void refresh(ctrl.signal);
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keys.userId]);

  async function upload() {
    if (!keys.userId) {
      toast.error("Run the diagnostic first");
      return;
    }
    if (!file || !title.trim()) {
      toast.error("Pick a PDF and a title");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("user_id", keys.userId);
      fd.append("title", title.trim());
      fd.append("pdf", file);
      const res = await uploadForm<{ collection: string; pages: number; chunks: number }>("/rag/upload", fd);
      toast.success(`Indexed ${res.chunks} chunks across ${res.pages} pages`);
      setFile(null);
      setTitle("");
      void refresh();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function generateQuiz(collection: string) {
    setGenBusy(collection);
    setQuiz(null);
    setChosen({});
    setActiveCollection(collection);
    try {
      const res = await api<GroundedQuiz>("/rag/quiz", {
        method: "POST",
        body: {
          user_id: keys.userId,
          collection,
          topic_hint: topic.trim() || undefined,
          n_questions: 5,
        },
      });
      setQuiz(res);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setGenBusy(null);
    }
  }

  return (
    <div className="space-y-4 py-2">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Library className="size-5 text-accent" />
          NCERT Library
        </h1>
        <p className="text-sm text-muted-foreground">
          Upload any chapter PDF; the system will index it locally with Gemini
          embeddings and generate MCQs that cite the chapter pages directly.
        </p>
      </div>

      <Card>
        <CardContent className="p-6 space-y-3">
          <div className="grid sm:grid-cols-[1fr_auto] gap-3">
            <div className="space-y-2">
              <Label htmlFor="title">Chapter title</Label>
              <Input
                id="title"
                placeholder="NCERT Class 11 - Newton's Laws"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="flex flex-col items-stretch justify-end gap-2">
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Button variant="outline" onClick={() => inputRef.current?.click()}>
                <Upload className="size-4" /> {file ? file.name.slice(0, 30) : "Choose PDF"}
              </Button>
              <Button onClick={upload} disabled={busy || !file || !title.trim()}>
                {busy ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
                {busy ? "Indexing..." : "Index chapter"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="size-4 text-accent" /> Indexed chapters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {docsError ? (
              <div className="text-sm space-y-2">
                <p className="text-destructive">Could not load chapters.</p>
                <p className="text-xs text-muted-foreground">{docsError}</p>
                <Button size="sm" variant="outline" onClick={() => void refresh()}>Retry</Button>
              </div>
            ) : docs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No chapters yet. Upload one above.
              </p>
            ) : (
              docs.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between rounded-md border border-border bg-background/40 p-3"
                >
                  <div className="space-y-1">
                    <div className="font-medium">{d.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {d.pages} pages {" | "} {d.chunks} chunks {" | "}
                      {new Date(d.created_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => generateQuiz(d.collection)}
                    disabled={genBusy === d.collection}
                  >
                    {genBusy === d.collection ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Sparkles className="size-3" />
                    )}
                    Quiz me
                  </Button>
                </div>
              ))
            )}
            <div className="pt-2 space-y-2">
              <Label htmlFor="topic">Optional topic hint for next quiz</Label>
              <Input
                id="topic"
                placeholder="e.g. Newton's third law and friction"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-accent" /> Grounded quiz
              {activeCollection && (
                <Badge variant="outline" className="ml-1 max-w-[180px] truncate">
                  {activeCollection}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!quiz && !genBusy && (
              <p className="text-sm text-muted-foreground">
                Pick a chapter on the left and tap <em>Quiz me</em>. Each
                question will cite the page it came from.
              </p>
            )}
            {genBusy && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Embedding query, retrieving
                top-8 excerpts and generating MCQs...
              </div>
            )}
            {quiz && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {quiz.questions.map((q, i) => {
                  const sel = chosen[i];
                  return (
                    <div
                      key={i}
                      className="rounded-lg border border-border bg-background/40 p-4 space-y-2"
                    >
                      <div className="text-sm font-medium">
                        Q{i + 1}. {q.stem}
                      </div>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {q.options.map((opt, j) => {
                          const correct = sel !== undefined && j === q.correct_index;
                          const wrong = sel === j && j !== q.correct_index;
                          return (
                            <button
                              key={j}
                              onClick={() => setChosen((c) => ({ ...c, [i]: j }))}
                              className={`text-left text-xs rounded border px-3 py-2 transition ${
                                correct
                                  ? "border-success bg-success/10"
                                  : wrong
                                    ? "border-destructive bg-destructive/10"
                                    : sel === j
                                      ? "border-primary bg-primary/10"
                                      : "border-border hover:bg-input/40"
                              }`}
                            >
                              {String.fromCharCode(65 + j)}. {opt}
                            </button>
                          );
                        })}
                      </div>
                      {sel !== undefined && (
                        <div className="text-xs text-muted-foreground flex items-start gap-2">
                          {sel === q.correct_index ? (
                            <CheckCircle2 className="size-3 text-success mt-0.5" />
                          ) : (
                            <XCircle className="size-3 text-destructive mt-0.5" />
                          )}
                          {q.explanation}
                        </div>
                      )}
                    </div>
                  );
                })}

                {quiz.citations.length > 0 && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                      Citations
                    </div>
                    <div className="space-y-1.5">
                      {quiz.citations.map((c) => (
                        <div
                          key={c.index}
                          className="text-xs rounded border border-border/60 bg-input/30 p-2"
                        >
                          <span className="text-accent font-medium">
                            [Excerpt {c.index} - p.{c.page}]
                          </span>{" "}
                          {c.preview}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
