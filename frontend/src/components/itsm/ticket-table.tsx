import Link from "next/link";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { PRIORITY_LABELS } from "@/lib/ticket-priority";
import type { WorkflowListItem, WorkflowStatus } from "@/lib/types";

import { ReprocessButton } from "./reprocess-button";

// Trilho de status (FR-055): cor não é o único sinal — o `Tag` de texto ao
// lado continua existindo, a borda é uma adição, não substituição.
const STATUS: Record<WorkflowStatus, { label: string; tone: BadgeVariant; rail: string }> = {
  pending: { label: "Pendente", tone: "neutral", rail: "border-l-transparent" },
  processing: { label: "Processando", tone: "accent", rail: "border-l-transparent" },
  completed: { label: "Concluído", tone: "success", rail: "border-l-status-ok" },
  retry_scheduled: { label: "Retry agendado", tone: "warning", rail: "border-l-status-warn" },
  failed: { label: "Falha", tone: "danger", rail: "border-l-status-critical" },
  needs_human_review: { label: "Revisão humana", tone: "danger", rail: "border-l-status-critical" },
};

const PRIORITY_TONE: Record<string, BadgeVariant> = {
  urgent: "danger",
  high: "warning",
  medium: "neutral",
  low: "neutral",
};

// Squad canônica é "SQUAD-0N" (ver backend/app/domain/squads.py); exibição
// pedida é "SquadN" (sem hífen, sem zero à esquerda). Só apresentação — o
// valor que trafega no filtro/querystring continua sendo o canônico
// (specs/012, evita quebrar `?squad=SQUAD-04`).
const SQUAD_LABEL_RE = /^SQUAD-0*(\d+)$/;

export function formatSquadLabel(squadId: string): string {
  const match = SQUAD_LABEL_RE.exec(squadId);
  return match ? `Squad${match[1]}` : squadId;
}

export function TicketTable({
  items,
  backHref,
}: {
  items: WorkflowListItem[];
  /** Preserva o recorte de filtros na volta do detalhe (FR-021). */
  backHref: string;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticket</TableHead>
          <TableHead>Assunto</TableHead>
          <TableHead>Prioridade</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Squad</TableHead>
          <TableHead>SLA</TableHead>
          <TableHead>Issue Jira</TableHead>
          <TableHead>Ação</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => {
          const status = STATUS[item.status];
          return (
            <TableRow key={item.workflow_execution_id}>
              <TableCell className={`border-l-[3px] font-mono text-xs ${status.rail}`}>
                <Link
                  href={`/itsm/${item.workflow_execution_id}?back=${encodeURIComponent(backHref)}`}
                  className="text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                >
                  {item.ticket.source_ticket_id}
                </Link>
              </TableCell>
              {/* Conteúdo externo: renderizado como texto, nunca como HTML. */}
              <TableCell className="text-text">{item.ticket.subject}</TableCell>
              <TableCell>
                <Badge variant={PRIORITY_TONE[item.ticket.priority] ?? "neutral"}>
                  {PRIORITY_LABELS[item.ticket.priority] ?? item.ticket.priority}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={status.tone}>{status.label}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {item.squad_id ? formatSquadLabel(item.squad_id) : "—"}
              </TableCell>
              {/* Sem prazo na origem: nenhuma coluna de SLA existe no schema. */}
              <TableCell className="text-muted-foreground">
                <span title="sem prazo conhecido na origem">—</span>
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {item.jira_issue_key ?? "—"}
              </TableCell>
              <TableCell>
                {item.reprocess_eligible && <ReprocessButton id={item.workflow_execution_id} />}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
