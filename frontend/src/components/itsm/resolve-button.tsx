"use client";

import { useActionState, useRef } from "react";
import { CheckCircle2 } from "lucide-react";

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
import { resolveTicket, type ResolveState } from "@/app/actions";

const MESSAGE_TONE: Record<ResolveState["status"], string> = {
  success: "text-link",
  not_found: "text-muted-foreground",
  error: "text-muted-foreground",
};

// Idempotente no backend (FR-053): repetir o clique não é destrutivo, mas
// pedimos confirmação porque, ao contrário do reprocessar, não tem volta —
// a edição fica desabilitada depois disso.
export function ResolveButton({ id }: { id: string }) {
  const [state, formAction, isPending] = useActionState<ResolveState | null, FormData>(
    resolveTicket,
    null,
  );

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
          {isPending ? "Concluindo…" : "Marcar como concluído"}
        </AlertDialogTrigger>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogMedia>
              <CheckCircle2 />
            </AlertDialogMedia>
            <AlertDialogTitle>Marcar este chamado como concluído?</AlertDialogTitle>
            <AlertDialogDescription>
              A edição fica desabilitada depois disso.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => formRef.current?.requestSubmit()}>
              Concluir
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
