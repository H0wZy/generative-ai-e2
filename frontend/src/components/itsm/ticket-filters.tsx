"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/button";

const STATUS_OPTIONS = [
  ["", "Todos os status"],
  ["pending", "Pendente"],
  ["processing", "Processando"],
  ["retry_scheduled", "Retry agendado"],
  ["completed", "Concluído"],
  ["failed", "Falha"],
  ["needs_human_review", "Revisão humana"],
] as const;

const PRIORITY_OPTIONS = [
  ["", "Todas as prioridades"],
  ["urgent", "Urgente"],
  ["high", "Alta"],
  ["medium", "Média"],
  ["low", "Baixa"],
] as const;

const FIELD =
  "min-h-9 rounded-md border border-divider bg-surface px-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

// O recorte vive em `searchParams`, não em estado local: assim ele sobrevive
// à recarga e volta intacto do detalhe (FR-016, FR-021).
export function TicketFilters({ squads }: { squads: string[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function apply(form: FormData) {
    const next = new URLSearchParams();
    for (const key of ["q", "status", "priority", "squad"]) {
      const value = form.get(key);
      if (typeof value === "string" && value) next.set(key, value);
    }
    // Trocar o recorte volta para a primeira página.
    startTransition(() => router.replace(`/itsm?${next.toString()}`));
  }

  return (
    <form action={apply} className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted">Busca</span>
        <input
          name="q"
          type="search"
          aria-label="Buscar por assunto ou identificador"
          maxLength={120}
          defaultValue={params.get("q") ?? ""}
          placeholder="assunto ou identificador"
          className={FIELD}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted">Status</span>
        <select name="status" defaultValue={params.get("status") ?? ""} className={FIELD}>
          {STATUS_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted">Prioridade</span>
        <select name="priority" defaultValue={params.get("priority") ?? ""} className={FIELD}>
          {PRIORITY_OPTIONS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted">Squad</span>
        <select name="squad" defaultValue={params.get("squad") ?? ""} className={FIELD}>
          <option value="">Todas as squads</option>
          {squads.map((squad) => (
            <option key={squad} value={squad}>
              {squad}
            </option>
          ))}
        </select>
      </label>

      <Button type="submit" variant="primary" disabled={isPending}>
        {isPending ? "Filtrando…" : "Filtrar"}
      </Button>
      <Button type="button" variant="ghost" onClick={() => router.replace("/itsm")}>
        Limpar
      </Button>
    </form>
  );
}
