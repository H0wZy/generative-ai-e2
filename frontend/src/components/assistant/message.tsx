import { renderAssistantMarkdown } from "@/lib/markdown";
import type { AssistantStatus, RetrievedSource, TicketRefSource } from "@/lib/types";

import { Sources } from "./sources";

// Faixa distinta por status (FR-043): cada modo de falha tem texto próprio,
// não uma mensagem de erro genérica.
const STATUS_NOTICE: Record<Exclude<AssistantStatus, "answered">, string> = {
  rate_limited:
    "O provedor do modelo atingiu o limite de requisições. Os trechos recuperados estão abaixo.",
  unavailable:
    "O provedor do modelo não respondeu. Os trechos recuperados estão abaixo.",
  timeout:
    "O provedor do modelo demorou demais para responder. Os trechos recuperados estão abaixo.",
  disabled:
    "O assistente está desligado nesta instalação. Defina ASSISTANT_ENABLED e a chave do provedor.",
};

export function UserMessage({ text }: { text: string }) {
  return (
    <div className="self-end max-w-[46rem] rounded-lg bg-accent-800 px-3 py-2">
      <p className="whitespace-pre-wrap text-sm text-neutral-100">{text}</p>
    </div>
  );
}

export function AssistantMessageView({
  status,
  answer,
  sources,
  truncatedHistory,
  ticketContext,
}: {
  status: AssistantStatus;
  answer: string | null;
  sources: RetrievedSource[];
  truncatedHistory: boolean;
  ticketContext: TicketRefSource | null;
}) {
  return (
    <div className="flex max-w-[46rem] flex-col gap-2 self-start rounded-lg bg-surface px-3 py-2 shadow-sm">
      {status !== "answered" && (
        <p role="status" className="text-sm text-text">
          {STATUS_NOTICE[status]}
        </p>
      )}
      {answer && (
        <p className="whitespace-pre-wrap text-sm text-text">
          {renderAssistantMarkdown(answer)}
        </p>
      )}
      {status === "answered" && sources.length === 0 && !ticketContext && (
        <p className="text-xs text-muted">
          Resposta de conhecimento geral — nenhum trecho da documentação indexada foi usado.
        </p>
      )}
      {truncatedHistory && (
        <p className="text-xs text-muted">
          O histórico foi truncado para caber no contexto.
        </p>
      )}
      {ticketContext && (
        <div className="rounded-md border border-divider px-2 py-1.5 text-xs">
          <p className="font-mono text-muted">{ticketContext.jira_issue_key}</p>
          {/* Conteúdo externo não confiável: texto simples, igual sources[].content (FR-045). */}
          <p className="text-text">{ticketContext.subject}</p>
          <p className="text-muted">
            status: {ticketContext.status}
            {ticketContext.squad_id ? ` · squad: ${ticketContext.squad_id}` : ""}
          </p>
        </div>
      )}
      <Sources sources={sources} />
    </div>
  );
}
