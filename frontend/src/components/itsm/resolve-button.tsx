"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { resolveTicket, type ResolveState } from "@/app/actions";

const MESSAGE_TONE: Record<ResolveState["status"], string> = {
  success: "text-link",
  not_found: "text-muted",
  error: "text-muted",
};

// Idempotente no backend (FR-053): repetir o clique não é destrutivo, mas
// pedimos confirmação porque, ao contrário do reprocessar, não tem volta —
// a edição fica desabilitada depois disso.
export function ResolveButton({ id }: { id: string }) {
  const [state, formAction, isPending] = useActionState<ResolveState | null, FormData>(
    resolveTicket,
    null,
  );

  return (
    <div className="flex flex-col items-start gap-1">
      <form
        action={formAction}
        onSubmit={(event) => {
          const confirmed = window.confirm("Marcar este chamado como concluído?");
          if (!confirmed) event.preventDefault();
        }}
      >
        <input type="hidden" name="id" value={id} />
        <Button type="submit" disabled={isPending} className="text-xs">
          {isPending ? "Concluindo…" : "Marcar como concluído"}
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
