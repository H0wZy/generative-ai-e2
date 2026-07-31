import { BacklogTable } from "@/components/agile/backlog-table";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type { Availability, Epic, WorkItem } from "@/lib/types";

type BacklogView = { epics: Epic[]; items: WorkItem[] };

function EpicProgress({ epic }: { epic: Epic }) {
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm text-text">{epic.name}</span>
        <span className="text-xs tabular-nums text-muted">
          {epic.done_points} / {epic.total_points} pts
        </span>
      </div>
      <div className="h-1.5 w-full rounded-sm bg-neutral-800">
        <div
          className="h-full rounded-sm bg-accent-500"
          style={{ width: `${Math.round(epic.progress * 100)}%` }}
        />
      </div>
    </li>
  );
}

export default async function Backlog() {
  const result = await apiFetch<Availability<BacklogView>>("/api/v1/agile/backlog?limit=100");

  if (!result.ok) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState reason="unavailable" detail={result.error.message} />
      </div>
    );
  }
  if (!result.data.available) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState reason={result.data.reason} detail={result.data.detail} />
      </div>
    );
  }

  const { epics, items } = result.data.data;

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <header>
        <h2 className="text-xl font-semibold text-text">Backlog</h2>
        <p className="text-sm text-muted">{items.length} item(ns) na ordem de rank do Jira</p>
      </header>

      {epics.length > 0 && (
        <Card title="Progresso por épico">
          <ul className="flex flex-col gap-3">
            {epics.map((epic) => (
              <EpicProgress key={epic.key} epic={epic} />
            ))}
          </ul>
        </Card>
      )}

      <Card>
        {items.length > 0 ? (
          <BacklogTable items={items} />
        ) : (
          <EmptyState title="Backlog vazio" hint="Nenhum item fora do sprint neste board." />
        )}
      </Card>
    </div>
  );
}
