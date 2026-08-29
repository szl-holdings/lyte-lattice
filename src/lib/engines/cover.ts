import type { CoverClaim, CoverPolicy } from "../types";

export const LINE_PERILS: Record<CoverPolicy["line"], string[]> = {
  auto: ["collision", "comprehensive", "liability", "uninsured"],
  home: ["water", "fire", "theft", "wind", "liability"],
  commercial: ["liability", "property", "inland marine", "business interruption"],
};

export const ALL_PERILS = [
  "collision",
  "comprehensive",
  "liability",
  "uninsured",
  "water",
  "fire",
  "theft",
  "wind",
  "property",
  "inland marine",
  "business interruption",
] as const;

export function inferCause(narrative: string): string {
  const n = narrative.toLowerCase();
  const pairs: Array<[RegExp, string]> = [
    [/colli|rear-end|fender|hit my|hit another|crash/, "collision"],
    [/hail|theft of (?:the )?car|stolen vehicle|break-in.*car|vandal/, "comprehensive"],
    [/water|pipe|flood|leak|sprinkler/, "water"],
    [/fire|smoke|burn/, "fire"],
    [/theft|stolen|burgl/, "theft"],
    [/wind|storm|tornado|hurricane/, "wind"],
    [/slip|injury|bodily|third[- ]party|liability/, "liability"],
    [/cargo|inland|shipment/, "inland marine"],
    [/interrupt|cannot operate|shutdown/, "business interruption"],
  ];
  for (const [re, cause] of pairs) if (re.test(n)) return cause;
  return "unknown";
}

export function coverageCheck(policy: CoverPolicy, cause: string): { covered: boolean; reason: string } {
  if (policy.status !== "in-force") {
    return { covered: false, reason: `Policy ${policy.number} is ${policy.status}.` };
  }
  const allowed = new Set([...policy.perils, ...LINE_PERILS[policy.line]]);
  if (cause === "unknown") {
    return { covered: false, reason: "Cause of loss is not classified." };
  }
  if (!allowed.has(cause)) {
    return {
      covered: false,
      reason: `${cause} is not a covered peril on ${policy.line} policy ${policy.number}.`,
    };
  }
  return { covered: true, reason: `${cause} matches ${policy.line} perils on ${policy.number}.` };
}

export function perilMatrix(policy: CoverPolicy): { peril: string; covered: boolean }[] {
  const allowed = new Set([...policy.perils, ...LINE_PERILS[policy.line]]);
  return ALL_PERILS.map((peril) => ({ peril, covered: allowed.has(peril) }));
}

export function suggestedReserve(narrative: string, policy: CoverPolicy): number {
  const nums = [...narrative.matchAll(/\$?\s?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.\d{2})?/g)]
    .map((m) => Number(m[1].replace(/,/g, "")))
    .filter((n) => n >= 250 && n <= policy.limit);
  if (nums.length) return Math.min(policy.limit, Math.max(...nums));
  const base = policy.line === "auto" ? 8_500 : policy.line === "home" ? 18_000 : 45_000;
  return Math.min(policy.limit, base);
}

export function nextClaimNumber(existing: CoverClaim[]): string {
  const n = existing.length + 9001;
  return `CLM-${n}`;
}

export function remainingLimit(policy: CoverPolicy, claims: CoverClaim[]): number {
  const used = claims
    .filter((c) => c.policyId === policy.id && c.status !== "denied")
    .reduce((s, c) => s + c.reserve + c.paid, 0);
  return Math.max(0, policy.limit - used);
}
