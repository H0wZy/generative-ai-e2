import Link from "next/link";

import { TicketFilters } from "@/components/itsm/ticket-filters";
import { TicketTable } from "@/components/itsm/ticket-table";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type { WorkflowListResponse } from "@/lib/types";

const PAGE_SIZE = 25;

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

export default async function ItsmQueue({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const offset = Number.parseInt(first(params.offset), 10) || 0;

  const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  for (const key of ["q", "status", "priority", "squad"] as const) {
    const value = first(params[key]);
    if (value) query.set(key, value);
  }

  const [page, all] = await Promise.all([
    apiFetch<WorkflowListResponse>(`/api/v1/workflows?${query}`),
    // As squads do seletor vêm do que existe na fila, não de uma lista fixa.
    apiFetch<WorkflowListResponse>("/api/v1/workflows?limit=200"),
  ]);

  const squads = all.ok
    ? [...new Set(all.data.items.map((item) => item.squad_id).filter((s): s is string => !!s))].sort()
    : [];

  // Preserva o recorte na volta do detalhe (FR-021).
  const backHref = `/itsm?${query}`;

  function pageHref(nextOffset: number): string {
    const next = new URLSearchParams(query);
    next.set("offset", String(nextOffset));
    return `/itsm?${next}`;
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-text">Fila de tickets</h2>
          <p className="text-sm text-muted">
            {page.ok ? `${page.data.total} execução(ões) no recorte atual` : "total indisponível"}
          </p>
        </div>
        <Link
          href="/itsm/new"
          className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-neutral-100 transition-colors hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          Novo chamado
        </Link>
      </header>

      <TicketFilters squads={squads} />

      <Card>
        {!page.ok ? (
          <UnavailableState reason="unavailable" detail={page.error.message} />
        ) : page.data.items.length === 0 ? (
          <EmptyState
            title="Nenhum ticket neste recorte"
            hint="Ajuste os filtros ou limpe a busca."
          />
        ) : (
          <TicketTable items={page.data.items} backHref={backHref} />
        )}
      </Card>

      {page.ok && page.data.total > PAGE_SIZE && (
        <nav className="flex items-center justify-between gap-3 text-sm" aria-label="Paginação">
          {offset > 0 ? (
            <Link
              href={pageHref(Math.max(0, offset - PAGE_SIZE))}
              className="text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              Anterior
            </Link>
          ) : (
            <span className="text-muted">Anterior</span>
          )}
          <span className="text-muted tabular-nums">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, page.data.total)} de {page.data.total}
          </span>
          {offset + PAGE_SIZE < page.data.total ? (
            <Link
              href={pageHref(offset + PAGE_SIZE)}
              className="text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              Próxima
            </Link>
          ) : (
            <span className="text-muted">Próxima</span>
          )}
        </nav>
      )}
    </div>
  );
}
