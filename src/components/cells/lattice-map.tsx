import { CELLS, INNER_RING, OUTER_RING, type CellId } from "@/lib/cells";
import { useLyte } from "@/lib/store";
import { cn } from "@/lib/utils";

function ring(ids: readonly CellId[], r: number, cx = 50, cy = 48, start = -Math.PI / 2): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {};
  const n = ids.length;
  ids.forEach((id, i) => {
    const a = start + (i / n) * Math.PI * 2;
    out[id] = { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });
  return out;
}

const INNER_POS = ring(INNER_RING, 22);
const OUTER_POS = ring(OUTER_RING, 38, 50, 48, -Math.PI / 2 + Math.PI / 13);

const POS: Record<CellId, { x: number; y: number }> = {
  ...INNER_POS,
  ...OUTER_POS,
  lyte: { x: 50, y: 48 },
} as Record<CellId, { x: number; y: number }>;

function nodePos(id: CellId) {
  return POS[id] ?? { x: 50, y: 48 };
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
      <circle cx={50} cy={48} r={22} fill="none" stroke="var(--color-border)" strokeWidth={0.2} />
      <circle cx={50} cy={48} r={38} fill="none" stroke="var(--color-border)" strokeWidth={0.15} />
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
              strokeWidth={0.28}
              strokeOpacity={0.5}
            />
          );
        })}
      <circle cx={50} cy={48} r={6.2} fill="none" stroke="var(--color-border-strong)" strokeWidth={0.3} />
      {CELLS.map((c) => {
        const p = nodePos(c.id);
        const iso = isolated.includes(c.id);
        const on = highlight === c.id || liveId === c.id;
        const outer = OUTER_RING.includes(c.id);
        const labelY = p.y >= 48 ? 4.6 : -3.6;
        return (
          <g
            key={c.id}
            transform={`translate(${p.x} ${p.y})`}
            className={onSelect ? "cursor-pointer" : undefined}
            onClick={() => onSelect?.(c.id)}
          >
            <circle
              r={c.id === "lyte" ? 3.6 : on ? 2.6 : outer ? 2.05 : 2.4}
              fill={iso ? "var(--color-danger)" : on ? "var(--color-accent)" : "var(--color-elevated)"}
              stroke={on ? "var(--color-fg)" : "var(--color-border-strong)"}
              strokeWidth={0.32}
            />
            <text
              y={c.id === "lyte" ? 0.7 : labelY}
              textAnchor="middle"
              fill="var(--color-muted)"
              style={{ fontSize: c.id === "lyte" ? 2.2 : outer ? 1.85 : 2.05, fontFamily: "IBM Plex Sans, sans-serif" }}
            >
              {c.id === "lyte" ? "LYTE" : c.n}
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
