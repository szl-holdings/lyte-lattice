import type { CellId } from "./cells";
import { CELL_MAP } from "./cells";
import { gate } from "./run-ai";
import { useLyte } from "./store";

export type OrganReceipt = {
  cell: string;
  id: string;
  title: string;
  cited: string;
  job: string;
  not: string;
  honesty: string;
  status: "ok" | "warn" | "error" | "blocked" | string;
  output: unknown;
  energy_joule: number | null;
  energy_honesty: string;
  lambda: string;
  bind: string;
  receipt: {
    hash: string;
    signed: boolean;
    lambda: string;
    proven_trust: boolean;
    slsa: string;
    kind: string;
  };
};

export async function actOrgan(
  cell: CellId,
  payload: Record<string, unknown> = {},
): Promise<{ ok: true; receipt: OrganReceipt; durationMs: number } | { ok: false; error: string; receipt?: OrganReceipt }> {
  const g = gate(cell);
  const t0 = Date.now();
  if (!g.ok) {
    useLyte.getState().addTrace({
      cell,
      kind: "organ",
      name: "act",
      status: "blocked",
      durationMs: 0,
      output: g.reason,
    });
    return { ok: false, error: g.reason };
  }

  try {
    const res = await fetch("/api/act", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ cell, payload }),
    });
    const durationMs = Date.now() - t0;
    const data = (await res.json()) as OrganReceipt & { error?: string };
    if (!res.ok) {
      const err = data.error || `organ ${res.status}`;
      useLyte.getState().addTrace({
        cell,
        kind: "organ",
        name: CELL_MAP[cell].title,
        status: "error",
        durationMs,
        output: err,
      });
      return { ok: false, error: err, receipt: data.cell ? data : undefined };
    }
    const status =
      data.status === "blocked" ? "blocked" : data.status === "error" ? "error" : data.status === "warn" ? "warn" : "ok";
    useLyte.getState().addTrace({
      cell,
      kind: "organ",
      name: CELL_MAP[cell].title,
      status,
      durationMs,
      input: JSON.stringify(payload).slice(0, 400),
      output: JSON.stringify(data.output).slice(0, 800),
      meta: {
        hash: data.receipt?.hash,
        energy_honesty: data.energy_honesty,
        signed: data.receipt?.signed,
      },
    });
    if (data.status === "blocked" || data.status === "error") {
      return { ok: false, error: (data.output as { error?: string } | undefined)?.error || data.status, receipt: data };
    }
    return { ok: true, receipt: data, durationMs };
  } catch (err) {
    const durationMs = Date.now() - t0;
    const error = err instanceof Error ? err.message : "organ failed";
    useLyte.getState().addTrace({
      cell,
      kind: "organ",
      name: CELL_MAP[cell].title,
      status: "error",
      durationMs,
      output: error,
    });
    return { ok: false, error };
  }
}
