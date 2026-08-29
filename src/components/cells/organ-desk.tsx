import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import type { CellId } from "@/lib/cells";
import { CELL_MAP } from "@/lib/cells";
import { ORGAN_DESKS, valuesToPayload } from "@/lib/organ-desks";
import { actOrgan, type OrganReceipt } from "@/lib/organ";

function toneFor(status: string): "ok" | "warn" | "danger" | "muted" {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  if (status === "blocked" || status === "error") return "danger";
  return "muted";
}

export function ReceiptPanel({ receipt }: { receipt: OrganReceipt }) {
  const signed = receipt.receipt?.signed;
  const trust = receipt.receipt?.proven_trust;
  return (
    <Panel>
      <PanelHeader
        title="UNSIGNED-honest receipt"
        hint="Kernel re-seals every organ. Signatures and proven_trust stay false."
        action={
          <div className="flex flex-wrap gap-1.5">
            <Badge tone={toneFor(receipt.status)}>{receipt.status}</Badge>
            <Badge tone={receipt.honesty === "LIVE" ? "ok" : "warn"}>{receipt.honesty}</Badge>
            <Badge tone={receipt.energy_honesty === "MEASURED" ? "ok" : "danger"}>
              joule {receipt.energy_honesty}
            </Badge>
          </div>
        }
      />
      <dl className="grid gap-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">Cited</dt>
          <dd className="mt-0.5 text-muted">{receipt.cited}</dd>
        </div>
        <div>
          <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">Not</dt>
          <dd className="mt-0.5 text-muted">{receipt.not}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">Job</dt>
          <dd className="mt-0.5 text-muted">{receipt.job}</dd>
        </div>
        <div>
          <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">Hash</dt>
          <dd className="mt-0.5 break-all font-mono text-[11px] text-fg">{receipt.receipt?.hash}</dd>
        </div>
        <div>
          <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">Attestation</dt>
          <dd className="mt-0.5 text-muted">
            signed {String(Boolean(signed))} · proven_trust {String(Boolean(trust))} · Λ {receipt.lambda}
          </dd>
        </div>
      </dl>
      <pre className="mt-4 max-h-80 overflow-auto rounded-md border border-border bg-sunken p-3 font-mono text-xs text-fg">
        {JSON.stringify(receipt.output, null, 2)}
      </pre>
    </Panel>
  );
}

export function OrganDesk({ id }: { id: CellId }) {
  const spec = ORGAN_DESKS[id];
  const meta = CELL_MAP[id];
  const initial = useMemo(() => {
    const v: Record<string, string> = {};
    for (const f of spec?.fields ?? []) v[f.key] = f.def;
    return v;
  }, [spec]);
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<OrganReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(null);
    const payload = valuesToPayload(id, values);
    const res = await actOrgan(id, payload);
    setBusy(false);
    if (res.ok) {
      setReceipt(res.receipt);
      toast.success(`${meta.title} organ ${res.receipt.status}`);
      return;
    }
    if (res.receipt) setReceipt(res.receipt);
    setError(res.error);
    toast.error(res.error);
  }

  if (!spec) {
    return (
      <CellFrame id={id} kernel={false}>
        <Panel>
          <p className="text-sm text-muted">No desk spec for {id}.</p>
        </Panel>
      </CellFrame>
    );
  }

  return (
    <CellFrame id={id} kernel={false}>
      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <Panel>
          <PanelHeader title="Python organ" hint={spec.hint} />
          <div className="flex flex-col gap-3">
            {spec.fields.map((f) => (
              <Field key={f.key} label={f.label}>
                {f.kind === "textarea" ? (
                  <Textarea
                    value={values[f.key] ?? ""}
                    onChange={(e) => setValues((s) => ({ ...s, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                  />
                ) : f.kind === "select" ? (
                  <select
                    className="h-11 w-full rounded-sm border border-border bg-sunken px-3 text-sm text-fg"
                    value={values[f.key] ?? f.def}
                    onChange={(e) => setValues((s) => ({ ...s, [f.key]: e.target.value }))}
                  >
                    {(f.options ?? []).map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Input
                    value={values[f.key] ?? ""}
                    onChange={(e) => setValues((s) => ({ ...s, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                  />
                )}
              </Field>
            ))}
            <Button onClick={run} disabled={busy} className="mt-1">
              {busy ? "Acting…" : "Act organ"}
            </Button>
            {error ? <p className="text-sm text-danger">{error}</p> : null}
          </div>
        </Panel>
        {receipt ? (
          <ReceiptPanel receipt={receipt} />
        ) : (
          <Panel>
            <PanelHeader title="Receipt" hint="Act the organ to seal an UNSIGNED-honest receipt." />
            <p className="text-sm text-muted">
              Stdlib Python kernel. Cite {meta.cited}. Joule stays UNAVAILABLE unless RAPL actually reads.
            </p>
          </Panel>
        )}
      </div>
    </CellFrame>
  );
}
