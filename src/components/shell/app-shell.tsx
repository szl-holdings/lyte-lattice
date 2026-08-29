import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Toaster } from "sonner";
import { CELLS, isCellId, type CellId } from "@/lib/cells";
import { ESTATE } from "@/lib/estate";
import { useLyte } from "@/lib/store";
import { cn } from "@/lib/utils";
import { HydrateStore } from "./hydrate";
import { CellLink } from "./cell-link";
import { Activity, Hexagon } from "lucide-react";

function currentCell(pathname: string): CellId {
  const part = pathname.replace(/^\//, "").split("/")[0] ?? "";
  if (part && isCellId(part)) return part;
  return "lyte";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const cell = currentCell(pathname);
  const isolated = useLyte((s) => s.isolated);
  const traces = useLyte((s) => s.traces);
  const last = traces[0];

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-fg">
      <HydrateStore />
      <header className="flex h-14 items-center justify-between gap-3 border-b border-border px-3 sm:px-5">
        <Link to="/" className="flex items-center gap-2.5 min-w-0">
          <span className="flex size-8 items-center justify-center rounded-sm border border-border-strong bg-elevated text-accent">
            <Hexagon className="size-4" strokeWidth={1.75} />
          </span>
          <span className="min-w-0">
            <span className="block font-medium leading-none tracking-tight">LYTE</span>
            <span className="mt-0.5 block truncate font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
              Lattice · BIND hologram
            </span>
          </span>
        </Link>
        <div className="hidden items-center gap-3 text-xs text-muted sm:flex">
          <span className="inline-flex items-center gap-1.5">
            <Activity className="size-3.5 text-ok" />
            <span className="tabular">{isolated.length ? `${isolated.length} isolated` : "all bound"}</span>
          </span>
          {last ? (
            <span className="max-w-xs truncate font-mono text-[11px] text-subtle">
              {last.cell}/{last.name}
            </span>
          ) : null}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav className="hidden w-[220px] shrink-0 border-r border-border bg-sunken md:flex md:flex-col">
          <p className="px-4 pb-2 pt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-subtle">Cells</p>
          <div className="flex-1 overflow-y-auto pb-4">
            {CELLS.map((c) => {
              const active = c.id === cell;
              const iso = isolated.includes(c.id);
              return (
                <CellLink
                  key={c.id}
                  id={c.id}
                  className={cn(
                    "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-150",
                    active ? "bg-elevated text-fg" : "text-muted hover:bg-surface hover:text-fg",
                  )}
                >
                  <span className="w-9 shrink-0 font-mono text-[10px] uppercase tracking-wider text-subtle">
                    {c.n}
                  </span>
                  <span className="flex-1 truncate">{c.title}</span>
                  <span
                    className={cn("size-1.5 rounded-full", iso ? "bg-danger" : "bg-ok")}
                    title={iso ? "isolated" : "live"}
                  />
                </CellLink>
              );
            })}
          </div>
        </nav>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="rail-scroll flex gap-1 overflow-x-auto border-b border-border px-2 py-2 md:hidden">
            {CELLS.map((c) => {
              const active = c.id === cell;
              return (
                <CellLink
                  key={c.id}
                  id={c.id}
                  className={cn(
                    "shrink-0 rounded-sm px-3 py-2 text-xs font-medium",
                    active ? "bg-elevated text-fg" : "text-muted",
                  )}
                >
                  {c.title}
                </CellLink>
              );
            })}
          </div>
          <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>

      <footer className="flex h-8 items-center justify-between gap-3 border-t border-border bg-sunken px-3 font-mono text-[10px] uppercase tracking-wider text-subtle sm:px-5">
        <span className="min-w-0 truncate">
          BIND · not flagship ·{" "}
          <a href={ESTATE.product} className="text-muted hover:text-fg" target="_blank" rel="noreferrer">
            a-11-oy.com
          </a>{" "}
          not certified ·{" "}
          <a href={ESTATE.proof} className="text-muted hover:text-fg" target="_blank" rel="noreferrer">
            a11oy.net
          </a>
        </span>
        <span className="truncate">{last ? `${last.cell} ${last.status}` : "idle"}</span>
      </footer>
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--color-elevated)",
            border: "1px solid var(--color-border)",
            color: "var(--color-fg)",
            fontFamily: "IBM Plex Sans, sans-serif",
          },
        }}
      />
    </div>
  );
}
