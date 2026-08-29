import { useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { runJson } from "@/lib/run-ai";
import { useLyte } from "@/lib/store";
import { cn, uid } from "@/lib/utils";

function passLabel(n: number) {
  return `validated in ${n} pass${n === 1 ? "" : "es"}`;
}

export function SchemaView() {
  const schemas = useLyte((s) => s.schemas);
  const setOut = useLyte((s) => s.setSchemaOutput);
  const addSchemaTemplate = useLyte((s) => s.addSchemaTemplate);
  const [tid, setTid] = useState(schemas[0]?.id ?? "");
  const tpl = schemas.find((t) => t.id === tid) ?? schemas[0];
  const [instruction, setInstruction] = useState(
    "Insured Jane Ortiz reports a rear-end collision on 12th Ave, 18 Aug 2026. Shop quote $9800. Policy POL-AUTO-4412.",
  );
  const [busy, setBusy] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customSchema, setCustomSchema] = useState("");
  const [genError, setGenError] = useState<{ id: string; error: string } | null>(null);

  async function generate() {
    if (!tpl || busy) return;
    setBusy(true);
    const res = await runJson({
      cell: "schema",
      name: tpl.name,
      schema: tpl.schema,
      instruction,
    });
    setBusy(false);
    if (!res.ok) {
      toast.error(res.error);
      setGenError({ id: tpl.id, error: res.error });
      setOut(tpl.id, undefined, res.raw ?? "", res.attempts);
      return;
    }
    setGenError(null);
    setOut(tpl.id, res.value, res.raw, res.attempts);
    toast.success("Object validated.");
  }

  function addCustom() {
    const name = customName.trim();
    if (!name) {
      toast.error("Name the schema.");
      return;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(customSchema);
    } catch {
      toast.error("Schema is not parseable JSON.");
      return;
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      toast.error("Schema must be a JSON object.");
      return;
    }
    const id = uid("sch");
    addSchemaTemplate({
      id,
      name,
      description: "Custom schema",
      schema: parsed as Record<string, unknown>,
    });
    setTid(id);
    setCustomName("");
    setCustomSchema("");
    toast.success("Template added.");
  }

  async function copyObject() {
    if (!tpl?.lastOutput) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(tpl.lastOutput, null, 2));
      toast.success("Copied.");
    } catch {
      toast.error("Clipboard unavailable.");
    }
  }

  const tplError = genError && tpl && genError.id === tpl.id ? genError.error : null;
  const invalid = Boolean(tpl && !tpl.lastOutput && (tpl.lastRaw || tplError));

  return (
    <CellFrame id="schema">
      <div className="flex flex-wrap gap-2">
        {schemas.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTid(t.id)}
            className={cn(
              "min-h-11 rounded-sm border px-3 py-2 text-left text-sm",
              t.id === tpl?.id ? "border-accent bg-elevated" : "border-border bg-surface",
            )}
          >
            <span className="block font-medium">{t.name}</span>
            <span className="text-xs text-muted">{t.description}</span>
            {t.lastAttempts != null && t.lastOutput ? (
              <span className="mt-0.5 block text-[11px] text-subtle">{passLabel(t.lastAttempts)}</span>
            ) : null}
          </button>
        ))}
      </div>

      {tpl ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel>
            <PanelHeader title="Instruction" hint="Outlines / Instructor loop: generate, validate, repair once." />
            <Textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={8} />
            <div className="mt-3 flex justify-end">
              <Button type="button" disabled={busy} onClick={() => void generate()}>
                {busy ? "Constraining…" : "Generate"}
              </Button>
            </div>
          </Panel>
          <Panel>
            <PanelHeader
              title="JSON Schema"
              action={tpl.lastOutput ? <Badge tone="ok">valid</Badge> : invalid ? <Badge tone="danger">invalid</Badge> : undefined}
            />
            <pre className="max-h-64 overflow-auto rounded-md border border-border bg-sunken p-3 text-[11px] text-muted">
              {JSON.stringify(tpl.schema, null, 2)}
            </pre>
          </Panel>
        </div>
      ) : null}

      <Panel>
        <PanelHeader title="Custom schema" hint="Paste a JSON Schema object. It joins the template picker." />
        <div className="grid gap-3">
          <Field label="Name">
            <Input
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="Loss notice"
            />
          </Field>
          <Field label="JSON schema">
            <Textarea
              value={customSchema}
              onChange={(e) => setCustomSchema(e.target.value)}
              rows={8}
              placeholder='{"type":"object","properties":{"cause":{"type":"string"}},"required":["cause"]}'
              className="font-mono text-xs"
            />
          </Field>
          <div className="flex justify-end">
            <Button type="button" variant="secondary" onClick={addCustom}>
              Add template
            </Button>
          </div>
        </div>
      </Panel>

      {tpl?.lastOutput ? (
        <Panel>
          <PanelHeader
            title="Validated object"
            hint={tpl.lastAttempts != null ? passLabel(tpl.lastAttempts) : "Outlines / Instructor accepted this object."}
            action={
              <div className="flex items-center gap-2">
                <Badge tone="ok">valid</Badge>
                <Button type="button" variant="secondary" size="sm" onClick={() => void copyObject()}>
                  Copy
                </Button>
              </div>
            }
          />
          <pre className="overflow-auto rounded-md border border-border bg-sunken p-3 text-sm text-fg">
            {JSON.stringify(tpl.lastOutput, null, 2)}
          </pre>
        </Panel>
      ) : invalid ? (
        <Panel>
          <PanelHeader
            title="Invalid object"
            hint={
              tpl?.lastAttempts != null
                ? `failed after ${tpl.lastAttempts} pass${tpl.lastAttempts === 1 ? "" : "es"}`
                : "Schema check rejected the model output."
            }
            action={<Badge tone="danger">invalid</Badge>}
          />
          {tplError ? <p className="mb-3 text-sm text-danger">{tplError}</p> : <p className="mb-3 text-sm text-danger">Object failed schema validation.</p>}
          {tpl?.lastRaw ? (
            <pre className="overflow-auto rounded-md border border-border bg-sunken p-3 text-xs text-danger">
              {tpl.lastRaw}
            </pre>
          ) : (
            <p className="text-sm text-muted">No raw payload returned.</p>
          )}
        </Panel>
      ) : null}
    </CellFrame>
  );
}
