"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ResolveButton } from "@/components/itsm/resolve-button";
import { TicketForm, type TicketFormValues } from "@/components/itsm/ticket-form";
import { apiFetch } from "@/lib/api";
import type { WorkflowDetail } from "@/lib/types";

export function TicketEditPanel({
  id,
  initialValues,
  resolved,
}: {
  id: string;
  initialValues: TicketFormValues;
  resolved: boolean;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function handleSubmit(values: TicketFormValues) {
    setPending(true);
    setFeedback(null);

    const result = await apiFetch<WorkflowDetail>(`/api/v1/workflows/${id}/ticket`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(values),
    });

    setPending(false);
    if (!result.ok) {
      setFeedback(
        result.error.status === 409
          ? "Chamado já concluído — não é possível editar."
          : result.error.message,
      );
      return;
    }
    setFeedback("Alterações salvas.");
    router.refresh();
  }

  if (resolved) {
    return <p className="text-sm text-muted">Chamado concluído — edição desabilitada.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <TicketForm
        initialValues={initialValues}
        onSubmit={handleSubmit}
        submitLabel={pending ? "Salvando…" : "Salvar alterações"}
        disabled={pending}
      />
      {feedback && (
        <p role="status" className="text-xs text-muted">
          {feedback}
        </p>
      )}
      <div>
        <ResolveButton id={id} />
      </div>
    </div>
  );
}
