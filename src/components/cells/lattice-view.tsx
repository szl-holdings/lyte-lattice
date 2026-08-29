import { useState } from "react";
import { CellFrame } from "./cell-frame";
import { LatticeMap, OverlayLegend } from "./lattice-map";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { CELL_IDS, CELL_MAP, type CellId } from "@/lib/cells";
import { useLyte } from "@/lib/store";
import type { YawarAction } from "@/lib/types";
import { fmtTime, uid } from "@/lib/utils";

const OVERLAYS = ["sentra", "yawar"] as const;
const YAWAR_ACTIONS: YawarAction[] = ["isolate", "throttle", "redact", "human", "observe"];

const selectClass =
  "h-11 w-full rounded-sm border border-border bg-sunken px-3 text-sm text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70";

export function LatticeView() {
  const binds = useLyte((s) => s.binds);
  const rules = useLyte((s) => s.rules);
  const log = useLyte((s) => s.latticeLog);
  const isolated = useLyte((s) => s.isolated);
  const throttled = useLyte((s) => s.throttled);
  const humanLock = useLyte((s) => s.humanLock);
  const toggleBind = useLyte((s) => s.toggleBind);
  const toggleRule = useLyte((s) => s.toggleRule);
  const toggleIsolate = useLyte((s) => s.toggleIsolate);
  const clearHolds = useLyte((s) => s.clearHolds);
  const releaseThrottle = useLyte((s) => s.releaseThrottle);
  const releaseHuman = useLyte((s) => s.releaseHuman);
  const addRule = useLyte((s) => s.addRule);
  const emitLattice = useLyte((s) => s.emitLattice);

  const [fireTrigger, setFireTrigger] = useState("guard.block");
  const [ruleName, setRuleName] = useState("");
  const [ruleTrigger, setRuleTrigger] = useState("");
  const [overlay, setOverlay] = useState<(typeof OVERLAYS)[number]>("yawar");
  const [action, setAction] = useState<YawarAction>("isolate");
  const [target, setTarget] = useState<CellId>("serve");

  const hasHolds = isolated.length > 0 || throttled.length > 0 || humanLock.length > 0;

  function fire() {
    const trigger = fireTrigger.trim() || "guard.block";
    emitLattice({ trigger, cell: "lattice" });
  }

  function submitRule() {
    const name = ruleName.trim();
    const trigger = ruleTrigger.trim();
    if (!name || !trigger) return;
    addRule({
      id: uid("r"),
      name,
      trigger,
      overlay,
      action,
      target,
      enabled: true,
    });
    setRuleName("");
    setRuleTrigger("");
  }

  return (
    <CellFrame id="lattice">
      <Panel pad={false}>
        <div className="flex items-start justify-between gap-3 px-5 pt-5">
          <div>
            <h2 className="text-sm font-medium">Immune overlay</h2>
            <p className="mt-1 text-xs text-muted">SENTRA detects. YAWAR isolates, throttles, redacts, or escalates.</p>
          </div>
          <OverlayLegend />
        </div>
        <LatticeMap highlight="lattice" />
      </Panel>

      <div className="flex flex-wrap gap-2">
        {!hasHolds ? <Badge tone="ok">No YAWAR holds</Badge> : null}
        {isolated.map((id) => (
          <Button key={id} size="sm" variant="danger" onClick={() => toggleIsolate(id)}>
            Release {CELL_MAP[id].title}
          </Button>
        ))}
        {throttled.map((id) => (
          <Button key={`t-${id}`} size="sm" variant="secondary" onClick={() => releaseThrottle(id)}>
            Release throttle {CELL_MAP[id].title}
          </Button>
        ))}
        {humanLock.map((id) => (
          <Button key={`h-${id}`} size="sm" variant="secondary" onClick={() => releaseHuman(id)}>
            Release human {CELL_MAP[id].title}
          </Button>
        ))}
        <Button size="sm" variant="ghost" onClick={clearHolds}>
          Release all holds
        </Button>
      </div>

      <Panel>
        <PanelHeader title="Fire tester" hint="Emit a SENTRA trigger so operators can test YAWAR." />
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={fireTrigger}
            onChange={(e) => setFireTrigger(e.target.value)}
            placeholder="guard.block"
            aria-label="Trigger"
          />
          <Button type="button" onClick={fire}>
            Fire
          </Button>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Binds" hint="Disable a bind to drop that overlay edge." />
          <ul className="divide-y divide-border">
            {binds.map((b) => (
              <li key={b.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <span>
                  <span className="font-medium">{CELL_MAP[b.from].title}</span>
                  <span className="text-subtle"> → </span>
                  <span className="font-medium">{CELL_MAP[b.to].title}</span>
                  <span className="ml-2 font-mono text-[10px] uppercase text-subtle">{b.overlay}</span>
                </span>
                <Button size="sm" variant={b.enabled ? "secondary" : "ghost"} onClick={() => toggleBind(b.id)}>
                  {b.enabled ? "On" : "Off"}
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel>
          <PanelHeader title="Rules" hint="Guard blocks isolate Serve by default." />
          <ul className="divide-y divide-border">
            {rules.map((r) => (
              <li key={r.id} className="flex items-start justify-between gap-3 py-2.5">
                <div>
                  <p className="text-sm font-medium">{r.name}</p>
                  <p className="text-xs text-muted">
                    {r.overlay} · {r.trigger} · {r.action} {r.target}
                  </p>
                </div>
                <Button size="sm" variant={r.enabled ? "secondary" : "ghost"} onClick={() => toggleRule(r.id)}>
                  {r.enabled ? "On" : "Off"}
                </Button>
              </li>
            ))}
          </ul>
          <form
            className="mt-4 grid gap-3 border-t border-border pt-4"
            onSubmit={(e) => {
              e.preventDefault();
              submitRule();
            }}
          >
            <Field label="Name">
              <Input value={ruleName} onChange={(e) => setRuleName(e.target.value)} placeholder="Isolate Serve" />
            </Field>
            <Field label="Trigger">
              <Input
                value={ruleTrigger}
                onChange={(e) => setRuleTrigger(e.target.value)}
                placeholder="guard.block"
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Overlay">
                <select
                  className={selectClass}
                  value={overlay}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === "sentra" || v === "yawar") setOverlay(v);
                  }}
                >
                  {OVERLAYS.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Action">
                <select
                  className={selectClass}
                  value={action}
                  onChange={(e) => {
                    const v = e.target.value as YawarAction;
                    if (YAWAR_ACTIONS.includes(v)) setAction(v);
                  }}
                >
                  {YAWAR_ACTIONS.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Target">
                <select
                  className={selectClass}
                  value={target}
                  onChange={(e) => {
                    const v = e.target.value;
                    if ((CELL_IDS as readonly string[]).includes(v)) setTarget(v as CellId);
                  }}
                >
                  {CELL_IDS.map((id) => (
                    <option key={id} value={id}>
                      {CELL_MAP[id].title}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <Button type="submit" disabled={!ruleName.trim() || !ruleTrigger.trim()}>
              Add rule
            </Button>
          </form>
        </Panel>
      </div>

      <Panel>
        <PanelHeader title="Overlay log" />
        {log.length === 0 ? (
          <p className="text-sm text-muted">No overlay events yet. Trip Guard or post a large Cover reserve.</p>
        ) : (
          <ul className="divide-y divide-border text-sm">
            {log.slice(0, 12).map((e, i) => (
              <li key={`${e.ts}-${i}`} className="flex flex-wrap gap-3 py-2">
                <span className="font-mono text-[11px] text-subtle tabular">{fmtTime(e.ts)}</span>
                <Badge tone={e.action === "isolate" ? "danger" : e.action === "observe" ? "muted" : "warn"}>
                  {e.action}
                </Badge>
                <span className="text-muted">{e.text}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </CellFrame>
  );
}
