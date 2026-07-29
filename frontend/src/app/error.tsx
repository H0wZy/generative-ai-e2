"use client";

import { ErrorState } from "@/components/ui/error-state";

// Fronteira de erro da raiz. `error.message` do servidor não é exibido: pode
// carregar detalhe interno. A cópia é do frontend.
export default function RootError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-6">
      <ErrorState
        title="Algo deu errado nesta página"
        message="Tente novamente. Se persistir, verifique se o backend está no ar."
        onRetry={reset}
      />
    </div>
  );
}
