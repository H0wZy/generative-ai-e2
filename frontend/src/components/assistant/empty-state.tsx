"use client";

import { ArrowUpRight, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "Onde está o quadro Kanban?",
  "Como funciona o roteamento para o Jira?",
  "Quais squads existem no projeto?",
  "Como funciona a idempotência do worker?",
];

export function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-16 text-center">
      <div className="mb-6 flex size-14 items-center justify-center rounded-2xl bg-v0-primary/10 text-v0-primary ring-1 ring-v0-primary/20">
        <Sparkles className="size-7" />
      </div>

      <h2 className="text-balance text-3xl font-semibold tracking-tight text-v0-foreground">
        Como posso ajudar hoje?
      </h2>
      <p className="mt-3 max-w-md text-pretty text-sm leading-relaxed text-v0-muted-foreground">
        Pesquise documentação, tickets, squads, processos e conhecimento interno do projeto ITSM +
        Agile.
      </p>

      <div className="mt-10 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSuggestion(suggestion)}
            className="group flex items-center justify-between gap-3 rounded-xl border border-v0-border bg-v0-card px-4 py-3.5 text-left text-sm text-v0-card-foreground transition-all hover:border-v0-primary/40 hover:bg-v0-accent"
          >
            <span className="text-pretty">{suggestion}</span>
            <ArrowUpRight className="size-4 shrink-0 text-v0-muted-foreground/50 transition-colors group-hover:text-v0-primary" />
          </button>
        ))}
      </div>
    </div>
  );
}
