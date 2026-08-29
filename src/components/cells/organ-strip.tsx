import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CellId } from "@/lib/cells";
import { ORGAN_DESKS, valuesToPayload } from "@/lib/organ-desks";
import { actOrgan, type OrganReceipt } from "@/lib/organ";
import { cn } from "@/lib/utils";

function toneFor(status: string): "ok" | "warn" | "danger" | "muted" {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  if (status === "blocked" || status === "error") return "danger";
  return "muted";
}

export function OrganStrip({ id }: { id: CellId }) {
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<OrganReceipt | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    const desk = ORGAN_DESKS[id];
    const values = Object.fromEntries((desk?.fields ?? []).map((f) => [f.key, f.def]));
    const res = await actOrgan(id, valuesToPayload(id, values));
    setBusy(false);
    if (res.ok) {
      setReceipt(res.receipt);
      toast.success("Python organ sealed.");
      return;
    }
    if (res.receipt) setReceipt(res.receipt);
    toast.error(res.error);
  }

  return (
    <div className="rounded-md border border-border bg-sunken px-3 py-3 sm:px-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-subtle">Python organ</span>
        {receipt ? (
          <>
            <Badge tone={toneFor(receipt.status)}>{receipt.status}</Badge>
            <span className="truncate font-mono text-[11px] text-muted">{receipt.receipt?.hash}</span>
          </>
        ) : (
          <span className="text-xs text-muted">Kernel receipts this cell. Cite, do not rehost.</span>
        )}
        <Button size="sm" variant="secondary" className={cn("ml-auto")} onClick={run} disabled={busy}>
          {busy ? "Acting…" : "Act"}
        </Button>
      </div>
    </div>
  );
}
