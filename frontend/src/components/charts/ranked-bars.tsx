import { EmptyState } from "@/components/ui/empty-state";

export type RankedRow = { label: string; count: number; muted?: boolean };

/** Barras horizontais ranqueadas — categoria à esquerda, valor à direita. */
export function RankedBars({ rows, emptyLabel }: { rows: RankedRow[]; emptyLabel: string }) {
  if (rows.length === 0) {
    return <EmptyState title="Sem dados neste recorte" hint={emptyLabel} />;
  }

  const max = Math.max(...rows.map((row) => row.count), 1);

  return (
    <div className="flex flex-col gap-1.5">
      {rows.map((row) => (
        <div key={row.label} className="flex items-center gap-3 text-sm">
          <span className="w-44 shrink-0 truncate text-muted-foreground" title={row.label}>
            {row.label}
          </span>
          <span className="h-4 flex-1 overflow-hidden rounded-sm bg-elevated">
            <span
              className={`block h-full rounded-sm ${row.muted ? "bg-neutral-700" : "bg-accent-500"}`}
              style={{ width: `${(row.count / max) * 100}%` }}
            />
          </span>
          <span className="w-12 shrink-0 text-right tabular-nums text-text">{row.count}</span>
        </div>
      ))}
    </div>
  );
}
