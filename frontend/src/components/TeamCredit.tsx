import { Sparkles } from "lucide-react";

const FULL_CREDIT =
  "Developed by Team mc² (MCTE Coding Club) — faculty mentors Capt Ajay Prakash Sharma and Capt Amit Verma — for the Shekunj Agentic AI Hackathon, powered by Microsoft.";

type Variant = "header" | "hero" | "footer";

export function TeamCredit({ variant }: { variant: Variant }) {
  if (variant === "header") {
    return (
      <p
        className="hidden md:block max-w-[min(28rem,42vw)] text-[10px] sm:text-[11px] leading-snug text-muted-foreground/90 border-l border-primary/25 pl-2.5 ml-0.5 font-medium tracking-wide"
        title={FULL_CREDIT}
      >
        <span className="text-foreground/75">Team mc²</span>
        <span className="mx-1 text-border">·</span>
        <span className="italic font-normal">MCTE Coding Club</span>
        <span className="mx-1 text-border">·</span>
        <span className="text-msft">Shekunj</span>
        <span className="mx-0.5 opacity-60">×</span>
        <span className="text-msft font-semibold">Microsoft</span>
      </p>
    );
  }

  if (variant === "hero") {
    return (
      <div className="relative mt-5 max-w-xl rounded-xl border border-border/80 bg-gradient-to-br from-primary/[0.08] via-transparent to-accent/[0.06] px-4 py-3.5 shadow-sm">
        <div
          className="pointer-events-none absolute inset-0 rounded-xl opacity-[0.35]"
          style={{
            background:
              "radial-gradient(420px 120px at 0% 0%, oklch(0.55 0.18 280 / 0.12), transparent 55%), radial-gradient(380px 100px at 100% 100%, oklch(0.65 0.14 250 / 0.1), transparent 50%)",
          }}
        />
        <div className="relative flex gap-3">
          <div className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/20">
            <Sparkles className="size-4" aria-hidden />
          </div>
          <div className="space-y-1.5 min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Crafted with care
            </p>
            <p className="text-sm sm:text-[15px] leading-relaxed text-foreground/95">
              Developed by{" "}
              <span className="font-semibold text-primary">Team mc²</span>
              {" — "}
              <span className="italic text-accent/95">MCTE Coding Club</span>
              {" — "}
              <span className="font-medium">Capt Ajay Prakash Sharma</span>
              {" & "}
              <span className="font-medium">Capt Amit Verma</span>
              {" for the "}
              <span className="text-msft font-medium">Shekunj Agentic AI Hackathon</span>
              {", "}
              <span className="text-muted-foreground">powered by</span>{" "}
              <span className="text-msft font-semibold">Microsoft</span>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // footer
  return (
    <footer className="mt-auto border-t border-border/60 bg-muted/20 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-4 text-center text-xs sm:text-sm text-muted-foreground leading-relaxed">
        <p className="max-w-3xl mx-auto">
          <span className="font-semibold text-foreground/80">ParikshaMitra</span>
          {" — "}
          {FULL_CREDIT}
        </p>
      </div>
    </footer>
  );
}
