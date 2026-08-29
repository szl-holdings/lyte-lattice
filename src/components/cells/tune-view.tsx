import { useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { runComplete } from "@/lib/run-ai";
import { adapterJsonl, useLyte } from "@/lib/store";
import { downloadText, uid } from "@/lib/utils";
import type { TuneAdapter } from "@/lib/types";

const TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"] as const;

export function TuneView() {
  const mosaic = useLyte((s) => s.mosaic);
  const adapters = useLyte((s) => s.adapters);
  const addAdapter = useLyte((s) => s.addAdapter);
  const bindAdapter = useLyte((s) => s.bindAdapter);
  const [picked, setPicked] = useState<string[]>(["doc_claims"]);
  const [name, setName] = useState("Desk LoRA pack");
  const [rank, setRank] = useState(16);
  const [alpha, setAlpha] = useState(32);
  const [qlora, setQlora] = useState(false);
  const [modules, setModules] = useState<string[]>(["q_proj", "k_proj", "v_proj", "o_proj"]);
  const [busy, setBusy] = useState(false);

  function toggleDoc(id: string) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  }

  function toggleModule(id: string) {
    setModules((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));
  }

  async function build() {
    if (!picked.length) {
      toast.error("Select mosaic documents.");
      return;
    }
    if (!modules.length) {
      toast.error("Select at least one target module.");
      return;
    }
    setBusy(true);
    const docs = mosaic.filter((d) => picked.includes(d.id));
    const corpus = docs.map((d) => `${d.title}: ${d.text.slice(0, 500)}`).join("\n\n");
    let systemAddendum =
      "Stay inside the selected mosaic. Prefer named perils, serving profiles, and bind overlay language.";
    let fewshot = [
      {
        user: docs[0]?.chunks[0]?.text.slice(0, 160) ?? "When is FNOL opened?",
        assistant: docs[0]?.chunks[0]?.text.slice(0, 220) ?? "Open FNOL the hour of report.",
      },
    ];
    const res = await runComplete({
      cell: "tune",
      name: "adapter distill",
      engine: "sglang",
      user: `From this mosaic, write a 2-sentence system addendum and one few-shot pair as JSON {"system":"...","user":"...","assistant":"..."}.\n\n${corpus}`,
    });
    if (res.ok) {
      try {
        const json = JSON.parse(res.text.replace(/```json|```/g, "").trim()) as {
          system?: string;
          user?: string;
          assistant?: string;
        };
        if (json.system) systemAddendum = json.system;
        if (json.user && json.assistant) fewshot = [{ user: json.user, assistant: json.assistant }];
      } catch {
        systemAddendum = res.text.slice(0, 280);
      }
    }
    const ad: TuneAdapter = {
      id: uid("ad"),
      name,
      mosaicDocIds: picked,
      rank,
      alpha,
      modules: [...modules],
      systemAddendum,
      fewshot,
      bound: false,
      jsonlPreview: "",
      qlora,
    };
    ad.jsonlPreview = adapterJsonl(ad, mosaic);
    addAdapter(ad);
    setBusy(false);
    toast.success("Adapter pack built. Bind it to inject system and few-shot into Serve.");
  }

  return (
    <CellFrame id="tune">
      <p className="max-w-3xl text-sm text-muted">
        GPU weights are not trained here; the pack is a real adapter spec that changes Serve by injecting the
        distilled system and few-shot — one bound pack at a time.
      </p>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel>
          <PanelHeader title="Job spec" hint="Unsloth-style LoRA / QLoRA config distilled from the mosaic mix." />
          <div className="grid gap-3">
            <Field label="Adapter name">
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label={`Rank ${rank}`}>
              <input
                type="range"
                min={4}
                max={64}
                step={4}
                value={rank}
                onChange={(e) => setRank(Number(e.target.value))}
                className="accent-[var(--color-accent)]"
              />
            </Field>
            <Field label={`Alpha ${alpha}`}>
              <input
                type="range"
                min={8}
                max={128}
                step={8}
                value={alpha}
                onChange={(e) => setAlpha(Number(e.target.value))}
                className="accent-[var(--color-accent)]"
              />
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={qlora} onChange={(e) => setQlora(e.target.checked)} />
              QLoRA 4-bit
            </label>
            <div>
              <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-subtle">Target modules</p>
              <ul className="flex flex-wrap gap-2">
                {TARGET_MODULES.map((id) => (
                  <li key={id}>
                    <label className="flex items-center gap-2 rounded-sm border border-border bg-sunken px-2.5 py-1.5 text-sm">
                      <input type="checkbox" checked={modules.includes(id)} onChange={() => toggleModule(id)} />
                      <span className="font-mono text-[12px]">{id}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-subtle">Mosaic mix</p>
              <ul className="space-y-2">
                {mosaic.map((d) => (
                  <li key={d.id}>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={picked.includes(d.id)}
                        onChange={() => toggleDoc(d.id)}
                      />
                      {d.title}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
            <Button type="button" disabled={busy} onClick={() => void build()}>
              {busy ? "Distilling…" : "Build adapter"}
            </Button>
          </div>
        </Panel>
        <Panel>
          <PanelHeader
            title="Adapters"
            hint="Bind injects system + few-shot into Serve. Only one pack bound at a time."
          />
          <ul className="space-y-3">
            {adapters.map((a) => (
              <li key={a.id} className="rounded-md border border-border bg-sunken p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{a.name}</span>
                  <span className="flex flex-wrap gap-1">
                    {a.qlora ? <Badge tone="accent">QLoRA 4-bit</Badge> : <Badge tone="muted">LoRA</Badge>}
                    {a.bound ? <Badge tone="ok">bound</Badge> : <Badge>idle</Badge>}
                  </span>
                </div>
                <p className="mt-1 font-mono text-[11px] text-subtle">
                  r={a.rank} α={a.alpha} · {a.modules.join(", ")}
                </p>
                <p className="mt-2 text-xs text-muted">{a.systemAddendum}</p>
                {a.bound ? (
                  <p className="mt-2 text-xs text-muted">
                    Bound pack is live on Serve: system addendum and few-shot are injected into every completion.
                  </p>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" variant={a.bound ? "secondary" : "primary"} onClick={() => bindAdapter(a.id, !a.bound)}>
                    {a.bound ? "Unbind" : "Bind to Serve"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => downloadText(`${a.id}.jsonl`, a.jsonlPreview || adapterJsonl(a, mosaic))}
                  >
                    Export JSONL
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      {adapters[0] ? (
        <Panel>
          <PanelHeader title="JSONL preview" />
          <Textarea readOnly rows={8} value={adapters[0].jsonlPreview || adapterJsonl(adapters[0], mosaic)} />
        </Panel>
      ) : null}
    </CellFrame>
  );
}
