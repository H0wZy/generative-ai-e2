"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

// Toggle de escopo do Quadro (sprint atual vs. board completo) dentro da
// mesma tela — antes eram duas rotas/abas separadas (specs/009). Client
// component pequeno, deliberadamente fora de board.tsx: Board só sabe
// renderizar colunas/cards, não conhece a noção de "escopo" da API.
export function ScopeToggle({ scope }: { scope: "sprint" | "board" }) {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function setScope(next: "sprint" | "board") {
    if (next === scope || isPending) return;
    const query = new URLSearchParams(params);
    query.set("escopo", next);
    startTransition(() => router.replace(`/agile/quadro?${query.toString()}`));
  }

  const OPTIONS: { value: "sprint" | "board"; label: string }[] = [
    { value: "sprint", label: "Sprint atual" },
    { value: "board", label: "Board completo" },
  ];

  return (
    <div
      role="radiogroup"
      aria-label="Escopo do quadro"
      className="inline-flex shrink-0 rounded-lg border border-divider bg-surface p-0.5"
    >
      {OPTIONS.map((option) => {
        const active = option.value === scope;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={isPending}
            onClick={() => setScope(option.value)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-text"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
