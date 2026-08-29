import { useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { gate, retrieveHits, rerankHits, runComplete } from "@/lib/run-ai";
import { useLyte } from "@/lib/store";
import { uid } from "@/lib/utils";
import type { RetrieveHit } from "@/lib/types";

export function RetrieveView() {
  const memory = useLyte((s) => s.memory);
  const addMemory = useLyte((s) => s.addMemory);
  const addMemoryThread = useLyte((s) => s.addMemoryThread);
  const rag = useLyte((s) => s.ragTurns);
  const addRag = useLyte((s) => s.addRag);
  const [q, setQ] = useState("What peril covers a burst supply line in a kitchen?");
  const [hits, setHits] = useState<RetrieveHit[]>([]);
  const [busy, setBusy] = useState<"search" | "chat" | null>(null);
  const [note, setNote] = useState("");
  const [threadId, setThreadId] = useState(memory[0]?.id ?? "");
  const [grokRerank, setGrokRerank] = useState(false);
  const thread = memory.find((t) => t.id === threadId) ?? memory[0];

  async function collectHits(k: number, forceRerank: boolean) {
    let found = retrieveHits(q, k);
    if (forceRerank || grokRerank) {
      found = await rerankHits(q, found);
    }
    setHits(found);
    return found;
  }

  async function search() {
    const g = gate("retrieve");
    if (!g.ok) {
      toast.error(g.reason);
      return;
    }
    setBusy("search");
    try {
      await collectHits(6, false);
    } finally {
      setBusy(null);
    }
  }

  async function chat() {
    const g = gate("retrieve");
    if (!g.ok) {
      toast.error(g.reason);
      return;
    }
    setBusy("chat");
    try {
      const found = await collectHits(5, true);
      const mem = thread?.notes
        .slice(0, 6)
        .map((n) => `- ${n.text}`)
        .join("\n");
      const res = await runComplete({
        cell: "retrieve",
        name: "rag chat",
        engine: "sglang",
        extraSystem:
          "Answer only from the provided mosaic hits and memory. Cite document titles. If missing, say so.",
        user: [
          mem ? `Memory${thread ? ` (${thread.title})` : ""}:\n${mem}` : "",
          `Hits:\n${found.map((h, i) => `[${i + 1}] ${h.title}: ${h.text}`).join("\n\n")}`,
          `Question: ${q}`,
        ]
          .filter(Boolean)
          .join("\n\n"),
      });
      if (!res.ok) {
        toast.error(res.error);
        return;
      }
      addRag({ id: uid("rag"), q, a: res.text, hits: found, ts: Date.now() });
    } finally {
      setBusy(null);
    }
  }

  function newThread() {
    addMemoryThread("New thread");
    const created = useLyte.getState().memory[0];
    if (created) setThreadId(created.id);
  }

  return (
    <CellFrame id="retrieve">
      <Panel>
        <PanelHeader
          title="Query"
          hint="BM25 over mosaic chunks. Chat reranks with Grok by default. Search only if the box is checked."
        />
        <Textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button type="button" variant="secondary" disabled={busy !== null} onClick={() => void search()}>
            {busy === "search" ? "Searching…" : "Search"}
          </Button>
          <Button type="button" disabled={busy !== null} onClick={() => void chat()}>
            {busy === "chat" ? "Retrieving…" : "Chat with mosaic"}
          </Button>
          <label className="flex items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={grokRerank}
              onChange={(e) => setGrokRerank(e.target.checked)}
            />
            Grok rerank
          </label>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <PanelHeader title="Hits" />
          {hits.length === 0 ? (
            <p className="text-sm text-muted">Run a search. Mix weights in Mosaic change ranking.</p>
          ) : (
            <ol className="space-y-3">
              {hits.map((h, i) => (
                <li key={h.chunkId} className="rounded-md border border-border bg-sunken p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium">
                      {i + 1}. {h.title}
                    </span>
                    <span className="flex flex-wrap gap-1">
                      {h.rerank != null ? <Badge tone="accent">rerank {h.rerank}</Badge> : null}
                      <Badge tone="muted">{h.score.toFixed(2)}</Badge>
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-muted">{h.text}</p>
                </li>
              ))}
            </ol>
          )}
        </Panel>
        <div className="space-y-4">
          <Panel>
            <PanelHeader
              title="Memory threads"
              hint="Letta-style operator facts Graph and RAG can read. Pin to the selected thread."
              action={
                <Button size="sm" variant="secondary" type="button" onClick={newThread}>
                  New thread
                </Button>
              }
            />
            {memory.length === 0 ? (
              <p className="text-sm text-muted">Start a thread to pin operator facts.</p>
            ) : (
              <>
                <div className="mb-3 flex flex-wrap gap-2">
                  {memory.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setThreadId(t.id)}
                      className={`rounded-sm border px-3 py-2 text-left text-sm ${
                        t.id === thread?.id ? "border-accent bg-elevated" : "border-border bg-sunken"
                      }`}
                    >
                      <span className="block font-medium">{t.title}</span>
                      <span className="font-mono text-[10px] uppercase tracking-wider text-subtle">
                        {t.notes.length} notes
                      </span>
                    </button>
                  ))}
                </div>
                {thread ? (
                  <>
                    <ul className="mb-3 space-y-2 text-sm text-muted">
                      {thread.notes.length === 0 ? (
                        <li className="text-sm text-muted">No notes on this thread yet.</li>
                      ) : (
                        thread.notes.map((n) => (
                          <li key={n.id} className="rounded-sm border border-border bg-sunken px-3 py-2">
                            {n.text}
                          </li>
                        ))
                      )}
                    </ul>
                    <Field label="Pin a fact">
                      <Input value={note} onChange={(e) => setNote(e.target.value)} />
                    </Field>
                    <Button
                      className="mt-2"
                      size="sm"
                      type="button"
                      onClick={() => {
                        if (!note.trim() || !thread) return;
                        addMemory(thread.id, note.trim());
                        setNote("");
                      }}
                    >
                      Pin
                    </Button>
                  </>
                ) : null}
              </>
            )}
          </Panel>
          {rag[0] ? (
            <Panel>
              <PanelHeader title="Last answer" />
              <p className="text-xs text-subtle">{rag[0].q}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-muted">{rag[0].a}</p>
            </Panel>
          ) : null}
        </div>
      </div>
    </CellFrame>
  );
}
