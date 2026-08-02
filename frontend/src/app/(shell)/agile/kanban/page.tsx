import { Board } from "@/components/agile/board";
import { EmptyState } from "@/components/ui/empty-state";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type { Availability, BoardView } from "@/lib/types";

export default async function KanbanBoard() {
  const result = await apiFetch<Availability<BoardView>>("/api/v1/agile/board?scope=board");

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

  const { columns } = result.data.data;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4 md:p-6">
      <header className="shrink-0">
        <h2 className="text-xl font-semibold text-text">Quadro Kanban</h2>
        <p className="text-sm text-muted-foreground">Todas as issues do board</p>
      </header>
      {columns.length > 0 ? (
        <Board initialColumns={columns} />
      ) : (
        <EmptyState title="Board sem issues" />
      )}
    </div>
  );
}
