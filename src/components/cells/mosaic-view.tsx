import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { mixRecipe, mixSample } from "@/lib/engines/mix";
import { useLyte } from "@/lib/store";
import { downloadText, pct, uid } from "@/lib/utils";
import type { MosaicChunk } from "@/lib/types";

export function MosaicView() {
  const mosaic = useLyte((s) => s.mosaic);
  const upsert = useLyte((s) => s.upsertDoc);
  const remove = useLyte((s) => s.removeDoc);
  const setWeight = useLyte((s) => s.setDocWeight);
  const setQuality = useLyte((s) => s.setDocQuality);
  const [sel, setSel] = useState(mosaic[0]?.id ?? "");
  const doc = mosaic.find((d) => d.id === sel) ?? mosaic[0];
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("operator");
  const [text, setText] = useState("");
  const [drawn, setDrawn] = useState<MosaicChunk[]>([]);

  const tokens = mosaic.reduce((n, d) => n + d.chunks.reduce((a, c) => a + c.tokens, 0), 0);
  const mix = mosaic.reduce((n, d) => n + d.weight, 0) || 1;
  const recipe = useMemo(() => mixRecipe(mosaic), [mosaic]);

  function add() {
    if (!title.trim() || !text.trim()) {
      toast.error("Title and body required.");
      return;
    }
    const id = uid("doc");
    upsert({
      id,
      title: title.trim(),
      source: source.trim() || "operator",
      text: text.trim(),
      weight: 1,
      quality: 0.8,
      tags: ["own-data"],
    });
    setSel(id);
    setTitle("");
    setText("");
    toast.success("Document mixed into mosaic.");
  }

  function drawMix() {
    if (!mosaic.length) {
      toast.error("Mix documents first.");
      return;
    }
    setDrawn(mixSample(mosaic, 8, Date.now()));
  }

  function exportBlend() {
    if (!mosaic.length) {
      toast.error("Mix documents first.");
      return;
    }
    const rows = mixSample(mosaic, 20, Date.now()).map((c) => {
      const d = mosaic.find((x) => x.id === c.docId);
      return JSON.stringify({
        instruction: `Use the ${d?.title ?? "mosaic"} desk manual.`,
        input: c.text,
        output: c.text,
      });
    });
    downloadText("mosaic-mix.jsonl", rows.join("\n"));
    toast.success("Blend exported.");
  }

  function onRemove(id: string) {
    remove(id);
    if (sel === id) {
      const next = mosaic.find((d) => d.id !== id);
      setSel(next?.id ?? "");
    }
    setDrawn((prev) => prev.filter((c) => c.docId !== id));
  }

  return (
    <CellFrame id="mosaic">
      <div className="grid gap-3 sm:grid-cols-3">
        <Panel>
          <p className="font-mono text-[10px] uppercase tracking-wider text-subtle">Documents</p>
          <p className="mt-1 font-mono text-2xl tabular">{mosaic.length}</p>
        </Panel>
        <Panel>
          <p className="font-mono text-[10px] uppercase tracking-wider text-subtle">Tokens</p>
          <p className="mt-1 font-mono text-2xl tabular">{tokens}</p>
        </Panel>
        <Panel>
          <p className="font-mono text-[10px] uppercase tracking-wider text-subtle">Mix mass</p>
          <p className="mt-1 font-mono text-2xl tabular">{mix.toFixed(1)}</p>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Panel>
          <PanelHeader title="Corpus" hint="Weights and quality change BM25 mix, Tune JSONL sampling, and the recipe shares." />
          <ul className="space-y-3">
            {mosaic.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => setSel(d.id)}
                  className={`w-full rounded-md border px-3 py-2.5 text-left ${d.id === doc?.id ? "border-accent bg-elevated" : "border-border bg-sunken"}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{d.title}</span>
                    <Badge tone="muted">{d.chunks.length} chunks</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {d.source} · q {d.quality.toFixed(2)} · w {d.weight.toFixed(1)}
                  </p>
                </button>
                <label className="mt-1.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-subtle">
                  <span className="w-16 shrink-0">W {d.weight.toFixed(1)}</span>
                  <input
                    aria-label={`${d.title} weight`}
                    type="range"
                    min={0.2}
                    max={2}
                    step={0.1}
                    value={d.weight}
                    onChange={(e) => setWeight(d.id, Number(e.target.value))}
                    className="w-full accent-[var(--color-accent)]"
                  />
                </label>
                <label className="mt-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-subtle">
                  <span className="w-16 shrink-0">Q {d.quality.toFixed(2)}</span>
                  <input
                    aria-label={`${d.title} quality`}
                    type="range"
                    min={0.5}
                    max={1}
                    step={0.05}
                    value={d.quality}
                    onChange={(e) => setQuality(d.id, Number(e.target.value))}
                    className="w-full accent-[var(--color-accent)]"
                  />
                </label>
              </li>
            ))}
          </ul>
        </Panel>
        <div className="space-y-4">
          {doc ? (
            <Panel>
              <PanelHeader
                title={doc.title}
                hint={doc.tags.join(" · ")}
                action={
                  <Button variant="ghost" size="sm" onClick={() => onRemove(doc.id)}>
                    Remove
                  </Button>
                }
              />
              <p className="max-h-48 overflow-y-auto text-sm leading-relaxed text-muted">{doc.text}</p>
              <p className="mt-3 font-mono text-[11px] text-subtle">
                {doc.chunks.length} chunks · first {doc.chunks[0]?.tokens ?? 0} tok
              </p>
            </Panel>
          ) : null}
          <Panel>
            <PanelHeader title="Add own data" hint="Paste a handbook, policy, or desk note." />
            <div className="grid gap-3">
              <Field label="Title">
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </Field>
              <Field label="Source">
                <Input value={source} onChange={(e) => setSource(e.target.value)} />
              </Field>
              <Field label="Body">
                <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={5} />
              </Field>
              <Button type="button" onClick={add}>
                Mix document
              </Button>
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel>
          <PanelHeader
            title="Mix recipe"
            hint="Mosaic composition: share of weighted tokens per document."
            action={
              <Button type="button" size="sm" variant="secondary" onClick={exportBlend}>
                Export blend
              </Button>
            }
          />
          {recipe.length === 0 ? (
            <p className="text-sm text-muted">Add documents to compose a mix.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[16rem] text-left text-sm">
                <thead>
                  <tr className="font-mono text-[10px] uppercase tracking-wider text-subtle">
                    <th className="pb-2 pr-3 font-medium">Title</th>
                    <th className="pb-2 pr-3 font-medium">Share</th>
                    <th className="pb-2 font-medium">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {recipe.map((r, i) => (
                    <tr key={`${r.title}-${i}`} className="border-t border-border">
                      <td className="py-2 pr-3">{r.title}</td>
                      <td className="py-2 pr-3 font-mono tabular">{pct(r.share)}</td>
                      <td className="py-2 font-mono tabular">{r.tokens}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
        <Panel>
          <PanelHeader
            title="Streaming mix"
            hint="Eight chunks drawn proportional to weight × quality."
            action={
              <Button type="button" size="sm" onClick={drawMix}>
                Draw mix
              </Button>
            }
          />
          {drawn.length === 0 ? (
            <p className="text-sm text-muted">Draw a mix to preview the streaming sample.</p>
          ) : (
            <ol className="space-y-2">
              {drawn.map((c, i) => {
                const titleForChunk = mosaic.find((d) => d.id === c.docId)?.title ?? c.docId;
                return (
                  <li key={`${c.id}-${i}`} className="rounded-md border border-border bg-sunken p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">
                        {i + 1}. {titleForChunk}
                      </span>
                      <Badge tone="muted">{c.tokens} tok</Badge>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-muted">{c.text}</p>
                  </li>
                );
              })}
            </ol>
          )}
        </Panel>
      </div>
    </CellFrame>
  );
}
