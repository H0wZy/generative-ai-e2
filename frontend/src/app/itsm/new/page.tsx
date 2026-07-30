"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { TicketForm, type TicketFormValues } from "@/components/itsm/ticket-form";
import { Card } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";

interface IngestResponse {
  workflow_execution_id: string;
}

export default function NewTicketPage() {
  const router = useRouter();
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
    router.push(`/itsm/${ingest.data.workflow_execution_id}`);
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <header>
        <h2 className="text-xl font-semibold text-text">Novo chamado</h2>
      </header>

      <Card className="max-w-2xl">
        <TicketForm
          onSubmit={handleSubmit}
          submitLabel={pending ? "Criando…" : "Criar chamado"}
          disabled={pending}
        />
        {failure && (
          <p role="alert" className="mt-3 text-sm text-text">
            {failure}
          </p>
        )}
      </Card>
    </div>
  );
}
