import type { ReactNode } from "react";
import { CELL_MAP, RICH_CELLS, type CellId } from "@/lib/cells";
import { useLyte } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { OrganStrip } from "./organ-strip";

export function CellFrame({
  id,
  children,
  kernel,
}: {
  id: CellId;
  children: ReactNode;
  kernel?: boolean;
}) {
  const meta = CELL_MAP[id];
  const isolated = useLyte((s) => s.isolated.includes(id));
  const throttled = useLyte((s) => s.throttled.includes(id));
  const human = useLyte((s) => s.humanLock.includes(id));
  const toggle = useLyte((s) => s.toggleIsolate);
  const showKernel = kernel ?? (id !== "lyte" && RICH_CELLS.includes(id));

  return (
    <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5 px-4 py-5 sm:px-6 sm:py-7">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-subtle">{meta.n}</span>
            <h1 className="text-2xl font-medium tracking-tight sm:text-3xl">{meta.title}</h1>
            <Badge tone={meta.honesty === "STRUCTURAL-ONLY" ? "warn" : "ok"}>
              {meta.honesty === "STRUCTURAL-ONLY" ? "Structural-only" : "Live"}
            </Badge>
            {isolated ? <Badge tone="danger">Isolated</Badge> : null}
            {throttled ? <Badge tone="warn">Throttled</Badge> : null}
            {human ? <Badge tone="warn">Human lock</Badge> : null}
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted">{meta.blurb}</p>
          <p className="mt-1 font-mono text-[11px] text-subtle">
            Cited {meta.cited} · Engine {meta.engine}
          </p>
        </div>
        {id !== "lyte" ? (
          <Button variant={isolated ? "secondary" : "ghost"} size="sm" onClick={() => toggle(id)}>
            {isolated ? "Release isolate" : "Isolate cell"}
          </Button>
        ) : null}
      </header>
      {showKernel ? <OrganStrip id={id} /> : null}
      {children}
    </div>
  );
}
