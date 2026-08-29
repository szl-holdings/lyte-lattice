export type JsonSchema = Record<string, unknown>;

function typeOf(v: unknown): string {
  if (v === null) return "null";
  if (Array.isArray(v)) return "array";
  return typeof v;
}

export function extractJson(text: string): string | null {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) return fenced[1].trim();
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start >= 0 && end > start) return text.slice(start, end + 1);
  const a0 = text.indexOf("[");
  const a1 = text.lastIndexOf("]");
  if (a0 >= 0 && a1 > a0) return text.slice(a0, a1 + 1);
  return null;
}

export function parseJsonLoose(text: string): unknown {
  const raw = extractJson(text) ?? text;
  return JSON.parse(raw);
}

export function validateSchema(value: unknown, schema: JsonSchema, path = "$"): string[] {
  const errors: string[] = [];
  const t = schema.type;
  if (typeof t === "string") {
    if (t === "object" && (typeOf(value) !== "object" || value === null || Array.isArray(value))) {
      errors.push(`${path} expected object`);
      return errors;
    }
    if (t === "array" && !Array.isArray(value)) {
      errors.push(`${path} expected array`);
      return errors;
    }
    if (t === "string" && typeof value !== "string") errors.push(`${path} expected string`);
    if (t === "number" && typeof value !== "number") errors.push(`${path} expected number`);
    if (t === "integer" && (!Number.isInteger(value) as boolean)) errors.push(`${path} expected integer`);
    if (t === "boolean" && typeof value !== "boolean") errors.push(`${path} expected boolean`);
  }
  if (schema.enum && Array.isArray(schema.enum) && !schema.enum.includes(value as never)) {
    errors.push(`${path} not in enum`);
  }
  if (t === "object" && value && typeof value === "object" && !Array.isArray(value)) {
    const obj = value as Record<string, unknown>;
    const props = (schema.properties ?? {}) as Record<string, JsonSchema>;
    const req = (schema.required ?? []) as string[];
    for (const r of req) {
      if (!(r in obj)) errors.push(`${path}.${r} required`);
    }
    for (const [k, sub] of Object.entries(props)) {
      if (k in obj) errors.push(...validateSchema(obj[k], sub, `${path}.${k}`));
    }
  }
  if (t === "array" && Array.isArray(value) && schema.items && typeof schema.items === "object") {
    value.forEach((item, i) => errors.push(...validateSchema(item, schema.items as JsonSchema, `${path}[${i}]`)));
  }
  return errors;
}

export function schemaPrompt(schema: JsonSchema, instruction: string): string {
  return [
    "Reply with ONLY valid JSON. No markdown, no commentary.",
    "The JSON must satisfy this JSON Schema:",
    JSON.stringify(schema),
    "",
    instruction,
  ].join("\n");
}

export function repairPrompt(schema: JsonSchema, raw: string, errors: string[]): string {
  return [
    "The previous JSON failed schema validation.",
    `Errors: ${errors.join("; ")}`,
    "Raw output:",
    raw.slice(0, 4000),
    "Schema:",
    JSON.stringify(schema),
    "Reply with ONLY corrected valid JSON.",
  ].join("\n");
}
