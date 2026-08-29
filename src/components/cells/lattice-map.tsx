import { CELLS, type CellId } from "@/lib/cells";
import { useLyte } from "@/lib/store";
import { cn } from "@/lib/utils";

const POS: Record<CellId, { x: number; y: number }> = {
  lyte: { x: 50, y: 48 },
  serve: { x: 50, y: 16 },
  graph: { x: 74, y: 28 },
  guard: { x: 26, y: 28 },
  mosaic: { x: 18, y: 52 },
  retrieve: { x: 28, y: 74 },
  schema: { x: 72, y: 74 },
  cover: { x: 88, y: 52 },
  quant: { x: 82, y: 18 },
  observe: { x: 50, y: 84 },
  tune: { x: 12, y: 18 },
  lattice: { x: 62, y: 48 },
};

function nodePos(id: CellId) {
  return POS[id];
}

export function LatticeMap({
  highlight,
  onSelect,
  liveId,
}: {
  highlight?: CellId;
  onSelect?: (id: CellId) => void;
  liveId?: string;
}) {
  const binds = useLyte((s) => s.binds);
  const isolated = useLyte((s) => s.isolated);

  return (
    <svg viewBox="0 0 100 100" className="h-auto w-full" role="img" aria-label="LYTE cell lattice">
      {binds
        .filter((b) => b.enabled)
        .map((b) => {
          const a = nodePos(b.from);
          const c = nodePos(b.to);
          const color =
            b.overlay === "sentra"
              ? "var(--color-warn)"
              : b.overlay === "yawar"
                ? "var(--color-danger)"
                : b.overlay === "data"
                  ? "var(--color-ok)"
                  : "var(--color-accent)";
          return (
            <line
              key={b.id}
              x1={a.x}
              y1={a.y}
              x2={c.x}
              y2={c.y}
              stroke={color}
              strokeWidth={0.35}
              strokeOpacity={0.55}
            />
          );
        })}
      <circle cx={50} cy={48} r={7.5} fill="none" stroke="var(--color-border-strong)" strokeWidth={0.3} />
      {CELLS.map((c) => {
        const p = nodePos(c.id);
        const iso = isolated.includes(c.id);
        const on = highlight === c.id || liveId === c.id;
        return (
          <g
            key={c.id}
            transform={`translate(${p.x} ${p.y})`}
            className={onSelect ? "cursor-pointer" : undefined}
            onClick={() => onSelect?.(c.id)}
          >
            <circle
              r={on ? 3.4 : 2.8}
              fill={iso ? "var(--color-danger)" : on ? "var(--color-accent)" : "var(--color-elevated)"}
              stroke={on ? "var(--color-fg)" : "var(--color-border-strong)"}
              strokeWidth={0.35}
            />
            <text
              y={5.8}
              textAnchor="middle"
              fill="var(--color-muted)"
              style={{ fontSize: 2.4, fontFamily: "IBM Plex Sans, sans-serif" }}
            >
              {c.title}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function OverlayLegend() {
  const items = [
    { label: "SENTRA", color: "bg-warn" },
    { label: "YAWAR", color: "bg-danger" },
    { label: "Data", color: "bg-ok" },
    { label: "Control", color: "bg-accent" },
  ];
  return (
    <ul className="flex flex-wrap gap-3 text-[11px] uppercase tracking-wider text-muted">
      {items.map((i) => (
        <li key={i.label} className="inline-flex items-center gap-1.5">
          <span className={cn("size-1.5 rounded-full", i.color)} />
          {i.label}
        </li>
      ))}
    </ul>
  );
}
