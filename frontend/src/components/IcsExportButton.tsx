"use client";

import { CalendarDays } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/Button";
import { API_URL } from "@/lib/api";
import { cn } from "@/lib/cn";

type Props = Omit<ButtonProps, "asChild" | "children"> & {
  userId: string;
  label?: string;
};

/**
 * Tiny anchor-styled-as-button that downloads the user's weekly plan as
 * an .ics calendar file. Hidden when there is no userId (pre-onboarding).
 */
export function IcsExportButton({ userId, label = "Add to calendar", className, variant = "outline", size = "sm", ...rest }: Props) {
  if (!userId) return null;
  const href = `${API_URL}/calendar/${encodeURIComponent(userId)}.ics`;
  return (
    <Button
      asChild
      variant={variant}
      size={size}
      className={cn(className)}
      {...rest}
    >
      <a href={href} download={`parikshamitra-${userId}.ics`}>
        <CalendarDays className="size-4" />
        <span className="hidden sm:inline">{label}</span>
      </a>
    </Button>
  );
}
