import type { CellId } from "../cells";
import type { LatticeRule, YawarAction } from "../types";

export type LatticeEvent = {
  trigger: string;
  cell: CellId;
  detail?: string;
};

export type LatticeDecision = {
  ruleId: string;
  ruleName: string;
  action: YawarAction;
  target: CellId;
  reason: string;
};

export function matchTrigger(ruleTrigger: string, event: LatticeEvent): boolean {
  if (ruleTrigger === "*" || ruleTrigger === event.trigger) return true;
  if (ruleTrigger.endsWith(".*")) {
    const prefix = ruleTrigger.slice(0, -2);
    return event.trigger.startsWith(prefix);
  }
  if (ruleTrigger.includes(">")) {
    const [key, raw] = ruleTrigger.split(">");
    if (!event.trigger.startsWith(key.trim())) return false;
    const n = Number(event.detail ?? "");
    const th = Number(raw.trim());
    return Number.isFinite(n) && Number.isFinite(th) && n > th;
  }
  return event.trigger.startsWith(ruleTrigger);
}

export function evaluateLattice(rules: LatticeRule[], event: LatticeEvent): LatticeDecision[] {
  const out: LatticeDecision[] = [];
  for (const rule of rules) {
    if (!rule.enabled) continue;
    if (!matchTrigger(rule.trigger, event)) continue;
    out.push({
      ruleId: rule.id,
      ruleName: rule.name,
      action: rule.action,
      target: rule.target,
      reason: `${rule.overlay.toUpperCase()} ${rule.name}: ${event.trigger}${event.detail ? ` (${event.detail})` : ""}`,
    });
  }
  return out;
}
