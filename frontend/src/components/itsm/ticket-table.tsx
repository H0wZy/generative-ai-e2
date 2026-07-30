import Link from "next/link";

import { Table, Td, Th, Tr } from "@/components/ui/table";
import { Tag, type TagTone } from "@/components/ui/tag";
import type { WorkflowListItem, WorkflowStatus } from "@/lib/types";

import { ReprocessButton } from "./reprocess-button";

// Trilho de status (FR-055): cor não é o único sinal — o `Tag` de texto ao
// lado continua existindo, a borda é uma adição, não substituição.
const STATUS: Record<WorkflowStatus, { label: string; tone: TagTone; rail: string }> = {
  pending: { label: "Pendente", tone: "neutral", rail: "border-l-transparent" },
  processing: { label: "Processando", tone: "accent", rail: "border-l-transparent" },
  completed: { label: "Concluído", tone: "success", rail: "border-l-status-ok" },
  retry_scheduled: { label: "Retry agendado", tone: "warning", rail: "border-l-status-warn" },
  failed: { label: "Falha", tone: "danger", rail: "border-l-status-critical" },
  needs_human_review: { label: "Revisão humana", tone: "danger", rail: "border-l-status-critical" },
};

const PRIORITY_TONE: Record<string, TagTone> = {
  urgent: "danger",
  high: "warning",
  medium: "neutral",
  low: "neutral",
};

export function TicketTable({
  items,
  backHref,
}: {
  items: WorkflowListItem[];
  /** Preserva o recorte de filtros na volta do detalhe (FR-021). */
  backHref: string;
}) {
  return (
    <Table
      head={
        <>
          <Th>Ticket</Th>
          <Th>Assunto</Th>
          <Th>Prioridade</Th>
          <Th>Status</Th>
          <Th>Squad</Th>
          <Th>SLA</Th>
          <Th>Issue Jira</Th>
          <Th>Ação</Th>
        </>
      }
    >
      {items.map((item) => {
        const status = STATUS[item.status];
        return (
          <Tr key={item.workflow_execution_id}>
            <Td className={`border-l-[3px] font-mono text-xs ${status.rail}`}>
              <Link
                href={`/itsm/${item.workflow_execution_id}?back=${encodeURIComponent(backHref)}`}
                className="text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              >
                {item.ticket.source_ticket_id}
              </Link>
            </Td>
            {/* Conteúdo externo: renderizado como texto, nunca como HTML. */}
            <Td className="text-text">{item.ticket.subject}</Td>
            <Td>
              <Tag tone={PRIORITY_TONE[item.ticket.priority] ?? "neutral"}>
                {item.ticket.priority}
              </Tag>
            </Td>
            <Td>
              <Tag tone={status.tone}>{status.label}</Tag>
            </Td>
            <Td className="text-muted">{item.squad_id ?? "—"}</Td>
            {/* Sem prazo na origem: nenhuma coluna de SLA existe no schema. */}
            <Td className="text-muted">
              <span title="sem prazo conhecido na origem">—</span>
            </Td>
            <Td className="font-mono text-xs text-muted">{item.jira_issue_key ?? "—"}</Td>
            <Td>
              {item.reprocess_eligible && (
                <ReprocessButton id={item.workflow_execution_id} />
              )}
            </Td>
          </Tr>
        );
      })}
    </Table>
  );
}
