import { Board } from "@/components/agile/board";
import { ScopeToggle } from "@/components/agile/scope-toggle";
import { EmptyState } from "@/components/ui/empty-state";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type { Availability, BoardView } from "@/lib/types";

// Consolidação de /agile/scrum + /agile/kanban num único "Quadro" (specs/009)
// — as duas rotas eram o mesmo componente Board com só o `scope` da API
// diferente, o que lia como bug de UI (tela duplicada) e não como duas
// features distintas.
export default async function QuadroPage({
  searchParams,
}: {
  searchParams: Promise<{ escopo?: string }>;
}) {
  const { escopo } = await searchParams;
  const scope: "sprint" | "board" = escopo === "board" ? "board" : "sprint";

  const result = await apiFetch<Availability<BoardView>>(`/api/v1/agile/board?scope=${scope}`);

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
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-text">Quadro</h2>
          <p className="text-sm text-muted-foreground">
            {scope === "sprint" ? "Itens do sprint ativo" : "Todas as issues do board"}
          </p>
        </div>
        <ScopeToggle scope={scope} />
      </header>
      {columns.length > 0 ? (
        <Board initialColumns={columns} />
      ) : (
        <EmptyState
          title={scope === "sprint" ? "Nenhum sprint ativo" : "Board sem issues"}
          hint={scope === "sprint" ? "Sem sprint em andamento não há quadro." : undefined}
        />
      )}
    </div>
  );
}
