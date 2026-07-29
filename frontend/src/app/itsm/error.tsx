"use client";

import { ErrorState } from "@/components/ui/error-state";

// Erro aqui não derruba o shell nem as demais seções (SC-008).
export default function ItsmError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-4 md:p-6">
      <ErrorState
        title="Não foi possível carregar a fila de tickets"
        message="A API de workflows não respondeu como esperado."
        onRetry={reset}
      />
    </div>
  );
}
