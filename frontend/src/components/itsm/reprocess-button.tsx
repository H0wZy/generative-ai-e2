"use client";

import { useActionState, useRef } from "react";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { runUndoable } from "@/lib/undoable";
import { reprocessWorkflow, type ReprocessState } from "@/app/actions";

const MESSAGE_TONE: Record<ReprocessState["status"], string> = {
  success: "text-link",
  conflict: "text-muted-foreground",
  not_found: "text-muted-foreground",
  error: "text-muted-foreground",
};

// A elegibilidade vem de `reprocess_eligible` da API (FR-019, FR-020): quem
// renderiza este botão já decidiu com o dado do servidor, não com uma lista
// de status repetida no cliente.
export function ReprocessButton({ id }: { id: string }) {
  const [state, formAction, isPending] = useActionState<ReprocessState | null, FormData>(
    reprocessWorkflow,
    null,
  );

  // A confirmação virou AlertDialog do produto: `window.confirm` bloqueia a
  // thread, ignora o tema e não é estilizável (specs/006).
  const formRef = useRef<HTMLFormElement>(null);

  return (
    <div className="flex flex-col items-start gap-1">
      <form ref={formRef} action={formAction}>
        <input type="hidden" name="id" value={id} />
      </form>

      <AlertDialog>
        <AlertDialogTrigger
          render={<Button type="button" disabled={isPending} className="text-xs" />}
        >
          {isPending ? "Reprocessando…" : "Reprocessar"}
        </AlertDialogTrigger>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogMedia>
              <RefreshCw />
            </AlertDialogMedia>
            <AlertDialogTitle>Reprocessar o workflow {id}?</AlertDialogTitle>
            <AlertDialogDescription>
              A ação é idempotente e não cria uma nova issue Jira.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                // Reprocessar é idempotente no backend, mas não tem volta —
                // então "desfazer" aqui cancela ANTES de disparar, em vez de
                // reverter depois.
                runUndoable({
                  message: "Reprocessamento agendado",
                  description: `Workflow ${id}`,
                  onCommit: () => formRef.current?.requestSubmit(),
                })
              }
            >
              Reprocessar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {state && (
        <p className={`max-w-52 text-xs ${MESSAGE_TONE[state.status]}`} role="status">
          {state.message}
        </p>
      )}
    </div>
  );
}
