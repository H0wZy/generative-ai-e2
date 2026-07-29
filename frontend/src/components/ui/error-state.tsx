import type { ReactNode } from "react";

import { Button } from "./button";

/** Exceção real. Indisponibilidade nomeada usa `unavailable-state` (FR-030). */
export function ErrorState({
  title = "Não foi possível carregar esta seção",
  message,
  onRetry,
}: {
  title?: string;
  message?: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
      <div>
        <p className="text-sm font-medium text-text">{title}</p>
        {message && <p className="mt-1 text-xs text-muted">{message}</p>}
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Tentar novamente
        </Button>
      )}
    </div>
  );
}
