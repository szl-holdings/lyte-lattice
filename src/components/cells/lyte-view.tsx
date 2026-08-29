import { useNavigate } from "@tanstack/react-router";
import { CELLS } from "@/lib/cells";
import { ESTATE, FRONTIERS } from "@/lib/estate";
import { useLyte } from "@/lib/store";
import { CellFrame } from "./cell-frame";
import { LatticeMap, OverlayLegend } from "./lattice-map";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { CellLink } from "@/components/shell/cell-link";
import { fmtTime } from "@/lib/utils";

function honestyTone(h: string): "ok" | "warn" | "danger" | "muted" {
  if (h === "LIVE") return "ok";
  if (h === "STRUCTURAL-ONLY") return "warn";
  if (h === "UNAVAILABLE") return "danger";
  return "muted";
}

export function LyteView() {
  const navigate = useNavigate();
  const traces = useLyte((s) => s.traces);
  const isolated = useLyte((s) => s.isolated);
  const binds = useLyte((s) => s.binds);
  const rules = useLyte((s) => s.rules);
  const claims = useLyte((s) => s.claims);
  const mosaic = useLyte((s) => s.mosaic);
  const adapter = useLyte((s) => s.adapters.find((a) => a.bound));

  const live = CELLS.filter((c) => c.honesty === "LIVE").length - isolated.filter((id) => id !== "lyte").length;
  const enabledBinds = binds.filter((b) => b.enabled).length;

  return (
    <CellFrame id="lyte">
      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Panel pad={false} className="overflow-hidden">
          <div className="flex items-start justify-between gap-3 px-5 pt-5">
            <div>
              <h2 className="text-sm font-medium">Bind map</h2>
              <p className="mt-1 text-xs text-muted">
                Design-partner hub. N1–N12 run in this hologram — tap a node to open it.
              </p>
            </div>
            <OverlayLegend />
          </div>
          <div className="px-2 pb-2 pt-1">
            <LatticeMap
              highlight="lyte"
              onSelect={(id) => {
                if (id === "lyte") navigate({ to: "/" });
                else navigate({ to: "/$cell", params: { cell: id } });
              }}
            />
          </div>
        </Panel>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <Panel>
            <PanelHeader title="Lattice health" hint="Counts from the live store, not a mock." />
            <dl className="grid grid-cols-2 gap-3">
              {[
                ["Live cells", String(live)],
                ["Isolated", String(isolated.length)],
                ["Binds on", String(enabledBinds)],
                ["YAWAR rules", String(rules.filter((r) => r.enabled).length)],
                ["Mosaic docs", String(mosaic.length)],
                ["Open claims", String(claims.filter((c) => c.status !== "closed" && c.status !== "denied").length)],
              ].map(([k, v]) => (
                <div key={k} className="rounded-md border border-border bg-sunken px-3 py-3">
                  <dt className="font-mono text-[10px] uppercase tracking-wider text-subtle">{k}</dt>
                  <dd className="mt-1 font-mono text-xl tabular text-fg">{v}</dd>
                </div>
              ))}
            </dl>
            {adapter ? (
              <p className="mt-4 text-xs text-muted">
                Bound adapter <span className="text-fg">{adapter.name}</span> on Serve (r={adapter.rank}).
              </p>
            ) : (
              <p className="mt-4 text-xs text-muted">No Tune adapter bound. Serve runs the raw engine profile.</p>
            )}
          </Panel>
          <Panel>
            <PanelHeader
              title="Honesty"
              hint="Lyte is STRUCTURAL-ONLY. Isolated is a YAWAR hold, not a roadmap."
            />
            <div className="max-h-56 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-subtle">
                  <tr className="border-b border-border">
                    <th className="py-2 font-medium">Cell</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {CELLS.map((c) => {
                    const iso = isolated.includes(c.id);
                    const label = iso ? "isolated" : c.honesty;
                    return (
                      <tr key={c.id} className="border-b border-border/70">
                        <td className="py-2">
                          <CellLink id={c.id} className="text-fg hover:text-accent">
                            {c.n} {c.title}
                          </CellLink>
                        </td>
                        <td className="py-2">
                          <Badge tone={iso ? "danger" : honestyTone(c.honesty)}>{label}</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>

      <Panel>
        <PanelHeader title="Named frontiers" hint="Cite the leader. Take the job. Do not rehost the code." />
        <div className="max-h-64 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-subtle">
              <tr className="border-b border-border">
                <th className="py-2 font-medium">Cell</th>
                <th className="py-2 font-medium">Cited job</th>
                <th className="py-2 font-medium">Honesty</th>
              </tr>
            </thead>
            <tbody>
              {FRONTIERS.map((f) => (
                <tr key={f.n} className="border-b border-border/70">
                  <td className="py-2 whitespace-nowrap">
                    {f.n} {f.title}
                  </td>
                  <td className="py-2 text-muted">{f.cited}</td>
                  <td className="py-2">
                    <Badge tone={honestyTone(f.honesty)}>{f.honesty}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-muted">
          Product{" "}
          <a className="text-fg hover:text-accent" href={ESTATE.product} target="_blank" rel="noreferrer">
            a-11-oy.com
          </a>{" "}
          is not certified. Proof{" "}
          <a className="text-fg hover:text-accent" href={ESTATE.proof} target="_blank" rel="noreferrer">
            a11oy.net
          </a>
          . Source{" "}
          <a className="text-fg hover:text-accent" href={ESTATE.source} target="_blank" rel="noreferrer">
            szl-holdings/lyte-lattice
          </a>
          . Hub RUNNING only after Immune readback. Λ = {ESTATE.lambda}.
        </p>
      </Panel>

      <Panel>
        <PanelHeader title="Recent spans" hint="Fed by every cell into Observe." />
        {traces.length === 0 ? (
          <p className="text-sm text-muted">Idle. Run Serve, Graph, Guard, Quant, or Cover to emit traces.</p>
        ) : (
          <ul className="divide-y divide-border">
            {traces.slice(0, 8).map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-sm">
                <span className="font-mono text-[11px] text-subtle tabular">{fmtTime(t.ts)}</span>
                <span className="w-20 font-medium capitalize">{t.cell}</span>
                <span className="text-muted">{t.name}</span>
                <Badge
                  tone={t.status === "ok" ? "ok" : t.status === "blocked" ? "danger" : t.status === "error" ? "danger" : "warn"}
                >
                  {t.status}
                </Badge>
                <span className="ml-auto font-mono text-[11px] text-subtle tabular">{t.durationMs}ms</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </CellFrame>
  );
}
