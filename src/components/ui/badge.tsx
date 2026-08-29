import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  children,
  tone = "muted",
  className,
}: {
  children: ReactNode;
  tone?: "muted" | "ok" | "warn" | "danger" | "accent";
  className?: string;
}) {
  const tones = {
    muted: "text-muted border-border bg-elevated",
    ok: "text-ok border-ok/30 bg-ok/10",
    warn: "text-warn border-warn/30 bg-warn/10",
    danger: "text-danger border-danger/30 bg-danger/10",
    accent: "text-accent border-accent/30 bg-accent/10",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[11px] tracking-wide uppercase",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
