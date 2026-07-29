"use client";

import { ErrorState } from "@/components/ui/error-state";

// Falha aqui não derruba o shell nem o workspace de ITSM (SC-008).
export default function AgileError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-4 md:p-6">
      <ErrorState
        title="Não foi possível carregar o workspace Agile"
        message="A integração com o Jira não respondeu como esperado."
        onRetry={reset}
      />
    </div>
  );
}
