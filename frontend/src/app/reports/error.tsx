"use client";

import { ErrorState } from "@/components/ui/error-state";

export default function ReportsError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-4 md:p-6">
      <ErrorState
        title="Não foi possível carregar os relatórios"
        message="A base analítica não respondeu como esperado."
        onRetry={reset}
      />
    </div>
  );
}
