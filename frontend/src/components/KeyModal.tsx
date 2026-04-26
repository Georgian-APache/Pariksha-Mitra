"use client";

import { useEffect, useState } from "react";
import { ExternalLink, KeyRound, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useApiKeys } from "@/lib/byok";

export function KeyModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [keys, setKeys] = useApiKeys();
  const [gemini, setGemini] = useState(keys.gemini);
  const [groq, setGroq] = useState(keys.groq);

  useEffect(() => {
    setGemini(keys.gemini);
    setGroq(keys.groq);
  }, [keys.gemini, keys.groq]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="size-5 text-accent" />
            Bring your own free API keys
          </DialogTitle>
          <DialogDescription>
            ParikshaMitra is zero-cost: each request uses your own free Gemini key. We
            never store it - it lives in your browser localStorage and is sent directly
            on each request.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="gemini-key" className="flex items-center gap-2">
              <Sparkles className="size-3.5 text-primary" /> Gemini API key (required)
            </Label>
            <Input
              id="gemini-key"
              type="password"
              placeholder="AIza..."
              value={gemini}
              onChange={(e) => setGemini(e.target.value)}
            />
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              Get one free at{" "}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-accent inline-flex items-center gap-1 hover:underline"
              >
                aistudio.google.com/apikey <ExternalLink className="size-3" />
              </a>{" "}
              - no credit card.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="groq-key">Groq API key (optional, for voice + fast LLM)</Label>
            <Input
              id="groq-key"
              type="password"
              placeholder="gsk_..."
              value={groq}
              onChange={(e) => setGroq(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Free at{" "}
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="text-accent hover:underline"
              >
                console.groq.com/keys
              </a>
              .
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={() => {
              setKeys({ gemini: gemini.trim(), groq: groq.trim() });
              toast.success("Keys saved locally");
              onOpenChange(false);
            }}
            disabled={!gemini.trim()}
          >
            Save keys
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
