"use client";

import { ErrorState } from "@/components/ui/error-state";

export default function AssistantError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-4 md:p-6">
      <ErrorState
        title="Não foi possível carregar o assistente"
        message="Tente novamente. A busca na documentação depende do serviço do RAG."
        onRetry={reset}
      />
    </div>
  );
}
