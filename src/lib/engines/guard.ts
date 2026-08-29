import { uid } from "../utils";
import type { GuardAction, GuardCategoryId, GuardHit, GuardPolicy, GuardVerdict } from "../types";

const PATTERNS: Record<
  GuardCategoryId,
  { label: string; llama: string; tests: Array<{ re: RegExp; evidence: string; weight: number }> }
> = {
  pii: {
    label: "PII",
    llama: "S7 Privacy",
    tests: [
      { re: /\b\d{3}-\d{2}-\d{4}\b/, evidence: "SSN-shaped number", weight: 0.95 },
      { re: /\b(?:\d[ -]*?){13,16}\b/, evidence: "card-shaped digit run", weight: 0.7 },
      { re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i, evidence: "email address", weight: 0.8 },
      { re: /\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b/, evidence: "phone number", weight: 0.75 },
    ],
  },
  secrets: {
    label: "Secrets",
    llama: "S7 Privacy",
    tests: [
      { re: /\bsk-[A-Za-z0-9]{12,}\b/, evidence: "secret-looking token", weight: 0.9 },
      { re: /\b(?:api[_-]?key|xai[_-]?api|bearer)\b/i, evidence: "credential keyword", weight: 0.55 },
      { re: /\bAKIA[0-9A-Z]{16}\b/, evidence: "AWS-like key", weight: 0.95 },
    ],
  },
  jailbreak: {
    label: "Jailbreak",
    llama: "S13 Code interpreter abuse",
    tests: [
      { re: /\bignore (?:all |previous |the )?instructions\b/i, evidence: "ignore-instructions", weight: 0.9 },
      { re: /\bdan mode\b/i, evidence: "DAN mode", weight: 0.85 },
      { re: /\bdeveloper override\b/i, evidence: "developer override", weight: 0.8 },
      { re: /\bjailbreak\b/i, evidence: "jailbreak mention", weight: 0.6 },
      { re: /\byou are now (?:unrestricted|uncensored)\b/i, evidence: "unrestricted persona", weight: 0.85 },
    ],
  },
  harm: {
    label: "Harm",
    llama: "S1 Violent crimes / S11 Self-harm",
    tests: [
      { re: /\b(?:build|make|assemble) a (?:bomb|weapon|explosive)\b/i, evidence: "weapons assembly", weight: 0.95 },
      { re: /\bhow to (?:harm|hurt|kill)\b/i, evidence: "harm how-to", weight: 0.9 },
      { re: /\b(?:suicide|self[- ]harm)\b/i, evidence: "self-harm mention", weight: 0.85 },
      { re: /\bindiscriminate (?:weapon|weapons)\b/i, evidence: "S9 weapons", weight: 0.8 },
    ],
  },
  injection: {
    label: "Injection",
    llama: "S13 Code interpreter abuse",
    tests: [
      { re: /```system/i, evidence: "system fence", weight: 0.7 },
      { re: /\bnew policy: always\b/i, evidence: "policy rewrite", weight: 0.8 },
      { re: /<\s*script\b/i, evidence: "script tag", weight: 0.75 },
      { re: /\bDROP TABLE\b/i, evidence: "SQL drop", weight: 0.8 },
    ],
  },
};

const REDACT = [
  { re: /\b\d{3}-\d{2}-\d{4}\b/g, with: "[SSN]" },
  { re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, with: "[EMAIL]" },
  { re: /\b(?:\d[ -]*?){13,16}\b/g, with: "[CARD]" },
  { re: /\bsk-[A-Za-z0-9]{12,}\b/g, with: "[SECRET]" },
  { re: /\bAKIA[0-9A-Z]{16}\b/g, with: "[KEY]" },
];

export const DEFAULT_GUARD_POLICY: GuardPolicy = {
  pii: "redact",
  secrets: "block",
  jailbreak: "block",
  harm: "block",
  injection: "block",
};

export const LLAMA_GUARD_TAXONOMY = [
  "S1 Violent crimes",
  "S2 Non-violent crimes",
  "S3 Sex-related crimes",
  "S6 Specialized advice",
  "S7 Privacy",
  "S9 Indiscriminate weapons",
  "S10 Hate",
  "S11 Suicide & self-harm",
  "S13 Code interpreter abuse",
] as const;

export function redactText(text: string): string {
  let out = text;
  for (const { re, with: w } of REDACT) out = out.replace(re, w);
  return out;
}

export function scanGuard(
  text: string,
  policy: GuardPolicy,
  direction: "prompt" | "response" = "prompt",
): GuardVerdict {
  const categories: GuardHit[] = (Object.keys(PATTERNS) as GuardCategoryId[]).map((id) => {
    const spec = PATTERNS[id];
    let score = 0;
    const evidence: string[] = [];
    for (const t of spec.tests) {
      if (t.re.test(text)) {
        score = Math.max(score, t.weight);
        evidence.push(t.evidence);
      }
    }
    return {
      id,
      label: spec.label,
      llama: spec.llama,
      hit: score >= 0.55,
      score,
      evidence: evidence.join(", "),
    };
  });

  const hits = categories.filter((c) => c.hit);
  let action: GuardAction = "allow";
  const reasons: string[] = [];
  for (const h of hits) {
    const want = policy[h.id];
    if (want === "block") {
      action = "block";
      reasons.push(`${h.label} block (${h.evidence})`);
    } else if (want === "redact" && action !== "block") {
      action = "redact";
      reasons.push(`${h.label} redact (${h.evidence})`);
    } else if (want === "allow") {
      reasons.push(`${h.label} allowed`);
    }
  }

  const redacted =
    action === "redact" || hits.some((h) => h.id === "pii" || h.id === "secrets") ? redactText(text) : text;

  return {
    id: uid("grd"),
    ts: Date.now(),
    text,
    direction,
    action,
    categories,
    redacted,
    reason: reasons.length ? reasons.join("; ") : "clean",
  };
}
