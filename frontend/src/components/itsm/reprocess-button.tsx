"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { reprocessWorkflow, type ReprocessState } from "@/app/actions";

const MESSAGE_TONE: Record<ReprocessState["status"], string> = {
  success: "text-link",
  conflict: "text-muted",
  not_found: "text-muted",
  error: "text-muted",
};

// A elegibilidade vem de `reprocess_eligible` da API (FR-019, FR-020): quem
// renderiza este botão já decidiu com o dado do servidor, não com uma lista
// de status repetida no cliente.
export function ReprocessButton({ id }: { id: string }) {
  const [state, formAction, isPending] = useActionState<ReprocessState | null, FormData>(
    reprocessWorkflow,
    null,
  );

  return (
    <div className="flex flex-col items-start gap-1">
      <form
        action={formAction}
        onSubmit={(event) => {
          const confirmed = window.confirm(
            `Reprocessar o workflow ${id}? A ação é idempotente e não cria uma nova issue Jira.`,
          );
          if (!confirmed) event.preventDefault();
        }}
      >
        <input type="hidden" name="id" value={id} />
        <Button type="submit" disabled={isPending} className="text-xs">
          {isPending ? "Reprocessando…" : "Reprocessar"}
        </Button>
      </form>
      {state && (
        <p className={`max-w-52 text-xs ${MESSAGE_TONE[state.status]}`} role="status">
          {state.message}
        </p>
      )}
    </div>
  );
}
