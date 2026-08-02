"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatSquadLabel } from "./ticket-table";

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

function FilterSelect({
  label,
  name,
  defaultValue,
  options,
}: {
  label: string;
  name: string;
  defaultValue: string;
  options: readonly (readonly [string, string])[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Select name={name} defaultValue={defaultValue} items={options.map(([value, l]) => ({ value, label: l }))}>
        <SelectTrigger className={`${FIELD} min-w-44 gap-2`} aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map(([value, l]) => (
            <SelectItem key={value} value={value} className="text-sm">
              {l}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}

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
        <span className="text-xs text-muted-foreground">Busca</span>
        <input
          name="q"
          type="search"
          aria-label="Buscar por assunto ou identificador"
          maxLength={120}
          defaultValue={params.get("q") ?? ""}
          placeholder="Assunto ou identificador..."
          className={FIELD}
        />
      </label>

      {/* `name` no Root faz o Select manter um input escondido, então o
          `action={apply}` continua lendo tudo por `FormData` como antes. */}
      <FilterSelect
        label="Status"
        name="status"
        defaultValue={params.get("status") ?? ""}
        options={STATUS_OPTIONS}
      />

      <FilterSelect
        label="Prioridade"
        name="priority"
        defaultValue={params.get("priority") ?? ""}
        options={PRIORITY_OPTIONS}
      />

      <FilterSelect
        label="Squad"
        name="squad"
        defaultValue={params.get("squad") ?? ""}
        options={[["", "Todas as squads"], ...squads.map((s) => [s, formatSquadLabel(s)] as const)]}
      />

      <Button type="submit" variant="default" disabled={isPending}>
        {isPending ? "Filtrando…" : "Filtrar"}
      </Button>
      <Button type="button" variant="ghost" onClick={() => router.replace("/itsm")}>
        Limpar
      </Button>
    </form>
  );
}
