"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus } from "lucide-react";

import { TicketForm, type TicketFormValues } from "@/components/itsm/ticket-form";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";

interface IngestResponse {
  workflow_execution_id: string;
}

/**
 * Criação de chamado sem sair da fila: era a rota `/itsm/new`, virou diálogo
 * sobre `/itsm`. A fila continua no fundo, então dá para conferir o recorte
 * atual enquanto preenche, e cancelar não custa uma navegação de volta.
 */
export function NewTicketDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function handleSubmit(values: TicketFormValues) {
    setPending(true);
    setFailure(null);

    // Mesmo id serve de event_id (chave de idempotência) e de
    // source_ticket_id: não existe sistema externo aqui, então não há um
    // identificador de origem melhor que o gerado no clique (contracts/api-tickets.md §Fluxo).
    const id = crypto.randomUUID();
    const ingest = await apiFetch<IngestResponse>("/api/v1/tickets/ingest", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        event_id: id,
        occurred_at: new Date().toISOString(),
        source_ticket_id: id,
        subject: values.subject,
        description: values.description,
        priority: values.priority,
        category: values.category || null,
      }),
    });

    if (!ingest.ok) {
      setPending(false);
      setFailure(ingest.error.message);
      return;
    }

    await apiFetch("/api/v1/workflows/process-next", { method: "POST" });
    setPending(false);
    setOpen(false);
    router.push(`/itsm/${ingest.data.workflow_execution_id}`);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setFailure(null);
      }}
    >
      <DialogTrigger className="group flex items-center gap-3 rounded-lg border border-divider bg-surface px-3.5 py-2.5 text-left transition-colors hover:border-muted-foreground/40 hover:bg-elevated focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated text-muted-foreground transition-colors group-hover:bg-surface group-hover:text-text"
        >
          <Plus className="size-4" />
        </span>
        <span className="flex flex-col">
          <span className="text-sm font-medium text-text">Novo chamado</span>
          <span className="text-xs text-muted-foreground">Abrir um ticket manualmente</span>
        </span>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Novo chamado</DialogTitle>
          <DialogDescription>
            O chamado entra na fila e é roteado para uma squad automaticamente.
          </DialogDescription>
        </DialogHeader>

        <TicketForm
          onSubmit={handleSubmit}
          submitLabel={pending ? "Criando…" : "Criar chamado"}
          disabled={pending}
        />

        {failure && (
          <p role="alert" className="text-sm text-destructive">
            {failure}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
