"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";

type Props = { children: ReactNode };
type S = { error: Error | null };

/**
 * Catches render errors in the page subtree and shows a recoverable message
 * instead of a blank white screen.
 */
export class AppErrorBoundary extends Component<Props, S> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): S {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    if (process.env.NODE_ENV === "development") {
      console.error("AppErrorBoundary", error.message, info.componentStack);
    }
  }

  override render() {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-lg rounded-xl border border-destructive/40 bg-destructive/10 p-6 text-center space-y-4">
          <h2 className="text-lg font-semibold text-foreground">Something went wrong</h2>
          <p className="text-sm text-muted-foreground">
            {this.state.error.message || "An unexpected error occurred."}
          </p>
          <Button
            type="button"
            onClick={() => {
              this.setState({ error: null });
              window.location.reload();
            }}
          >
            Reload page
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
