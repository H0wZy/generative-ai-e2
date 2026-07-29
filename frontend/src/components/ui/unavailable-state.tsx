import type { AvailabilityReason } from "@/lib/types";

// Indisponibilidade nomeada não é exceção (FR-030): a seção renderiza, diz a
// causa e orienta a configuração. `detail` vem do backend e é texto curto de
// diagnóstico, nunca corpo de erro cru.
const REASON_COPY: Record<AvailabilityReason, { title: string; hint: string }> = {
  not_configured: {
    title: "Integração com o Jira não configurada",
    hint: "Defina JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN e JIRA_BOARD_ID no backend.",
  },
  unauthorized: {
    title: "Credencial do Jira recusada",
    hint: "O token configurado não autenticou. Verifique e-mail e token da API.",
  },
  forbidden: {
    title: "Sem permissão no Jira",
    hint: "A credencial autenticou, mas não tem acesso a este board ou operação.",
  },
  unavailable: {
    title: "Jira indisponível no momento",
    hint: "A integração não respondeu. Tente novamente em instantes.",
  },
  rate_limited: {
    title: "Limite de requisições do Jira atingido",
    hint: "Aguarde alguns instantes antes de recarregar esta seção.",
  },
  no_transition: {
    title: "Transição indisponível",
    hint: "O Jira não oferece essa mudança de status para esta issue.",
  },
  already_there: {
    title: "A issue já está nessa coluna",
    hint: "Nenhuma alteração foi enviada ao Jira.",
  },
};

export function UnavailableState({
  reason,
  detail,
}: {
  reason: AvailabilityReason | null;
  detail?: string | null;
}) {
  const copy = reason ? REASON_COPY[reason] : null;
  return (
    <div className="flex flex-col items-center gap-1 px-4 py-10 text-center">
      <p className="text-sm font-medium text-text">
        {copy?.title ?? "Seção indisponível"}
      </p>
      <p className="text-xs text-muted">{copy?.hint}</p>
      {detail && <p className="text-xs text-muted">{detail}</p>}
    </div>
  );
}
