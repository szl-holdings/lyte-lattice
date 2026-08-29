import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import {
  coverageCheck,
  inferCause,
  LINE_PERILS,
  nextClaimNumber,
  perilMatrix,
  remainingLimit,
  suggestedReserve,
} from "@/lib/engines/cover";
import { gate, runJson } from "@/lib/run-ai";
import { useLyte } from "@/lib/store";
import type { CoverClaim } from "@/lib/types";
import { money, uid } from "@/lib/utils";

function statusTone(s: CoverClaim["status"]) {
  if (s === "denied") return "danger" as const;
  if (s === "closed") return "muted" as const;
  if (s === "fnol") return "warn" as const;
  return "ok" as const;
}

export function CoverView() {
  const policies = useLyte((s) => s.policies);
  const claims = useLyte((s) => s.claims);
  const addClaim = useLyte((s) => s.addClaim);
  const patch = useLyte((s) => s.patchClaim);
  const postPayment = useLyte((s) => s.postPayment);
  const human = useLyte((s) => s.humanLock.includes("cover"));
  const schema = useLyte((s) => s.schemas.find((t) => t.id === "sch_claim"));
  const [pid, setPid] = useState(policies[0]?.id ?? "");
  const [narrative, setNarrative] = useState(
    "Jane Ortiz, POL-AUTO-4412. Rear-ended at a light. Body shop quote $9,800 for bumper and radiator.",
  );
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState(claims[0]?.id ?? "");
  const [noteDraft, setNoteDraft] = useState("");
  const [payAmt, setPayAmt] = useState("");
  const policy = policies.find((p) => p.id === pid) ?? policies[0];
  const claim = claims.find((c) => c.id === openId) ?? claims[0];
  const claimPolicy = useMemo(
    () => policies.find((p) => p.id === claim?.policyId),
    [policies, claim],
  );

  const matrix = useMemo(() => (policy ? perilMatrix(policy) : []), [policy]);
  const remain = useMemo(
    () => (policy ? remainingLimit(policy, claims) : 0),
    [policy, claims],
  );
  const formPerils = policy ? LINE_PERILS[policy.line] : [];
  const previewCause = useMemo(() => inferCause(narrative), [narrative]);
  const previewCheck = useMemo(
    () => (policy ? coverageCheck(policy, previewCause) : null),
    [policy, previewCause],
  );
  const claimRemain = useMemo(
    () => (claimPolicy ? remainingLimit(claimPolicy, claims) : 0),
    [claimPolicy, claims],
  );
  const payValue = Number(payAmt);
  const canPay = Boolean(claim) && Number.isFinite(payValue) && payValue > 0;

  async function extractAndOpen() {
    const g = gate("cover");
    if (!g.ok) {
      toast.error(g.reason);
      return;
    }
    if (!policy || !narrative.trim()) return;
    setBusy(true);
    let extracted: Record<string, string> = {};
    if (schema) {
      const res = await runJson<Record<string, string | number>>({
        cell: "cover",
        name: "FNOL extract",
        schema: schema.schema,
        instruction: `Extract a P&C FNOL from:\n${narrative}\nPolicy ${policy.number} ${policy.insured} ${policy.line}.`,
      });
      if (res.ok) {
        extracted = Object.fromEntries(Object.entries(res.value).map(([k, v]) => [k, String(v)]));
        useLyte.getState().setSchemaOutput(schema.id, res.value, res.raw);
      } else toast.message(`Extract fallback: ${res.error}`);
    }
    const cause = extracted.cause || inferCause(narrative);
    const check = coverageCheck(policy, cause);
    const reserve = check.covered
      ? Number(extracted.reserveHint || suggestedReserve(narrative, policy))
      : 0;
    const rec: CoverClaim = {
      id: uid("clm"),
      number: nextClaimNumber(useLyte.getState().claims),
      policyId: policy.id,
      status: check.covered ? "open" : "denied",
      cause,
      narrative,
      lossDate: extracted.lossDate || new Date().toISOString().slice(0, 10),
      reserve,
      paid: 0,
      extracted,
      notes: [{ ts: Date.now(), text: `FNOL via Cover. ${check.reason}` }],
    };
    addClaim(rec);
    setOpenId(rec.id);
    setPayAmt("");
    if (reserve > 50000) {
      useLyte.getState().emitLattice({ trigger: "cover.reserve>", cell: "cover", detail: String(reserve) });
    }
    useLyte.getState().addTrace({
      cell: "cover",
      kind: "fnol",
      name: rec.number,
      status: check.covered ? "ok" : "warn",
      durationMs: 1,
      output: `${rec.status} ${cause} ${money(reserve)}`,
    });
    setBusy(false);
    toast.success(`${rec.number} ${rec.status}`);
  }

  function addNote() {
    if (!claim || !noteDraft.trim()) return;
    patch(claim.id, { notes: [{ ts: Date.now(), text: noteDraft.trim() }, ...claim.notes] });
    setNoteDraft("");
  }

  function closeClaim(kind: "closed" | "denied") {
    if (!claim) return;
    if (human && kind === "closed") {
      toast.error("YAWAR human lock — add a note before closing.");
      return;
    }
    patch(claim.id, {
      status: kind,
      notes: [...claim.notes, { ts: Date.now(), text: `Status set to ${kind}.` }],
    });
  }

  function postPay() {
    if (!claim || !canPay) return;
    postPayment(claim.id, payValue, noteDraft.trim() || undefined);
    setPayAmt("");
    toast.success(`Posted ${money(payValue)} on ${claim.number}`);
  }

  return (
    <CellFrame id="cover">
      <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
        <Panel>
          <PanelHeader title="Policies in force" hint="Guidewire-style P&C core, in-console." />
          <ul className="space-y-2">
            {policies.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => setPid(p.id)}
                  className={`w-full rounded-md border px-3 py-3 text-left ${p.id === policy?.id ? "border-accent bg-elevated" : "border-border bg-sunken"}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">{p.number}</span>
                    <Badge tone={p.status === "in-force" ? "ok" : "danger"}>{p.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm">
                    {p.insured} · {p.line}
                  </p>
                  <p className="text-xs text-muted">
                    Limit {money(p.limit)} · ded {money(p.deductible)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
          {policy ? (
            <div className="mt-4 border-t border-border pt-4">
              <p className="font-mono text-[10px] uppercase tracking-wider text-subtle">
                {policy.line} form · {formPerils.join(" · ")}
              </p>
              <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ["Premium", money(policy.premium)],
                  ["Limit", money(policy.limit)],
                  ["Deductible", money(policy.deductible)],
                  ["Remaining", money(remain)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-md border border-border bg-sunken px-3 py-2.5">
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">{k}</dt>
                    <dd className="mt-1 font-mono text-sm tabular">{v}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-3 max-h-48 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-subtle">
                    <tr>
                      <th className="py-1.5 font-medium">Peril</th>
                      <th className="py-1.5 font-medium">Covered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.map((row) => (
                      <tr key={row.peril} className="border-t border-border">
                        <td className="py-1.5 capitalize">{row.peril}</td>
                        <td className="py-1.5">
                          <Badge tone={row.covered ? "ok" : "muted"}>{row.covered ? "yes" : "no"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </Panel>
        <Panel>
          <PanelHeader title="FNOL" hint="Extracts structured fields, then coverage-checks the peril." />
          <Field label="Narrative">
            <Textarea value={narrative} onChange={(e) => setNarrative(e.target.value)} rows={6} />
          </Field>
          {previewCheck ? (
            <div className="mt-3 rounded-md border border-border bg-sunken px-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-subtle">
                  Coverage preview
                </span>
                <Badge tone={previewCheck.covered ? "ok" : "danger"}>
                  {previewCheck.covered ? "covered" : "not covered"}
                </Badge>
              </div>
              <p className="mt-2 text-sm capitalize">
                Cause {previewCause}
                {policy ? ` · ${policy.number}` : ""}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted">{previewCheck.reason}</p>
            </div>
          ) : null}
          <div className="mt-3 flex justify-end">
            <Button type="button" disabled={busy} onClick={() => void extractAndOpen()}>
              {busy ? "Extracting…" : "Open from narrative"}
            </Button>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
        <Panel>
          <PanelHeader title="Claims" />
          <ul className="space-y-2">
            {claims.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => {
                    setOpenId(c.id);
                    setPayAmt("");
                  }}
                  className={`w-full rounded-md border px-3 py-2.5 text-left text-sm ${c.id === claim?.id ? "border-accent bg-elevated" : "border-border bg-sunken"}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs">{c.number}</span>
                    <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                  </div>
                  <p className="mt-1 text-muted">
                    {c.cause} · {money(c.reserve)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
        {claim && claimPolicy ? (
          <Panel>
            <PanelHeader
              title={claim.number}
              hint={`${claimPolicy.insured} · ${claimPolicy.number}`}
              action={<Badge tone={statusTone(claim.status)}>{claim.status}</Badge>}
            />
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-subtle">Cause</dt>
                <dd className="capitalize">{claim.cause}</dd>
              </div>
              <div>
                <dt className="text-xs text-subtle">Loss date</dt>
                <dd className="tabular">{claim.lossDate}</dd>
              </div>
              <div>
                <dt className="text-xs text-subtle">Reserve</dt>
                <dd className="tabular">{money(claim.reserve)}</dd>
              </div>
              <div>
                <dt className="text-xs text-subtle">Paid</dt>
                <dd className="tabular">{money(claim.paid)}</dd>
              </div>
              <div>
                <dt className="text-xs text-subtle">Remaining limit</dt>
                <dd className="tabular">{money(claimRemain)}</dd>
              </div>
              <div>
                <dt className="text-xs text-subtle">Deductible</dt>
                <dd className="tabular">{money(claimPolicy.deductible)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-sm leading-relaxed text-muted">{claim.narrative}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <Field label="Payment amount">
                <Input
                  type="number"
                  min={0}
                  step="1"
                  value={payAmt}
                  onChange={(e) => setPayAmt(e.target.value)}
                  placeholder="0"
                />
              </Field>
              <Button type="button" size="sm" disabled={!canPay} onClick={postPay}>
                Post payment
              </Button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  patch(claim.id, {
                    status: "reserved",
                    reserve: suggestedReserve(claim.narrative, claimPolicy),
                  })
                }
              >
                Set suggested reserve
              </Button>
              <Button size="sm" variant="secondary" onClick={addNote} disabled={!noteDraft.trim()}>
                Add note
              </Button>
              <Button size="sm" variant="secondary" onClick={() => closeClaim("closed")}>
                Close
              </Button>
              <Button size="sm" variant="danger" onClick={() => closeClaim("denied")}>
                Deny
              </Button>
            </div>
            <Field label="File note">
              <Input value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)} />
            </Field>
            <Field label="Manual reserve">
              <Input
                type="number"
                defaultValue={claim.reserve}
                key={claim.id}
                onBlur={(e) => {
                  const n = Number(e.target.value);
                  if (!Number.isFinite(n)) return;
                  patch(claim.id, { reserve: n, status: n > 0 ? "reserved" : claim.status });
                  if (n > 50000) {
                    useLyte.getState().emitLattice({
                      trigger: "cover.reserve>",
                      cell: "cover",
                      detail: String(n),
                    });
                  }
                }}
              />
            </Field>
            <ul className="mt-4 space-y-2 text-xs text-muted">
              {claim.notes.map((n, i) => (
                <li key={i}>{n.text}</li>
              ))}
            </ul>
          </Panel>
        ) : null}
      </div>
    </CellFrame>
  );
}
