import Link from "next/link";
import { notFound } from "next/navigation";

import { ReprocessButton } from "@/components/itsm/reprocess-button";
import { TicketEditPanel } from "@/components/itsm/ticket-edit-panel";
import type { TicketFormValues } from "@/components/itsm/ticket-form";
import { Timeline } from "@/components/itsm/timeline";
import { formatSquadLabel } from "@/components/itsm/ticket-table";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import { PRIORITY_LABELS } from "@/lib/ticket-priority";
import type { WorkflowDetail } from "@/lib/types";

const LINK_CLASS =
  "text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm text-text">{children}</dd>
    </div>
  );
}

export default async function TicketDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ back?: string }>;
}) {
  const { id } = await params;
  const { back } = await searchParams;
  // Só um caminho interno volta: `back` vem da URL e não é confiável.
  const backHref = back?.startsWith("/itsm") ? back : "/itsm";

  const result = await apiFetch<WorkflowDetail>(`/api/v1/workflows/${id}`);
  if (!result.ok && result.error.status === 404) notFound();

  if (!result.ok) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState reason="unavailable" detail={result.error.message} />
      </div>
    );
  }

  const detail = result.data;

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href={backHref} className={LINK_CLASS}>
          ← Voltar para a fila
        </Link>
        {detail.reprocess_eligible && <ReprocessButton id={detail.workflow_execution_id} />}
      </div>

      <header className="flex flex-col gap-1">
        <p className="font-mono text-xs text-muted-foreground">{detail.ticket.source_ticket_id}</p>
        {/* Conteúdo externo não confiável: texto, nunca HTML. */}
        <h2 className="text-xl font-semibold text-text">{detail.ticket.subject}</h2>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Execução" className="lg:col-span-2">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Status">
              <Badge variant={detail.reprocess_eligible ? "danger" : "success"}>{detail.status}</Badge>
            </Field>
            <Field label="Tentativas">{detail.attempt_count}</Field>
            <Field label="Squad">{detail.squad_id ? formatSquadLabel(detail.squad_id) : "—"}</Field>
            <Field label="Confiança do roteamento">
              {detail.routing_confidence !== null
                ? `${Math.round(detail.routing_confidence * 100)}%`
                : "—"}
            </Field>
            <Field label="Regra">{detail.routing_rule_version ?? "—"}</Field>
            <Field label="Motivo do roteamento">{detail.routing_reason ?? "—"}</Field>
            {/* FR-020: a causa da falha precisa estar legível no detalhe. */}
            <Field label="Último erro">{detail.last_error ?? "—"}</Field>
            <Field label="Próxima tentativa">
              {detail.next_attempt_at
                ? new Date(detail.next_attempt_at).toLocaleString("pt-BR")
                : "—"}
            </Field>
          </dl>
        </Card>

        <Card title="Issue no Jira">
          {detail.jira_issue_key ? (
            <div className="flex flex-col gap-2">
              {detail.jira_issue_url ? (
                <a
                  href={detail.jira_issue_url}
                  target="_blank"
                  rel="noreferrer"
                  className={`font-mono text-sm ${LINK_CLASS}`}
                >
                  {detail.jira_issue_key}
                </a>
              ) : (
                <p className="font-mono text-sm text-text">{detail.jira_issue_key}</p>
              )}
              <p className="text-xs text-muted-foreground">
                origem do vínculo: {detail.link_origin ?? "—"}
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Nenhuma issue vinculada.</p>
          )}
        </Card>

        <Card title="Ticket" className="lg:col-span-2">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Prioridade">{PRIORITY_LABELS[detail.ticket.priority] ?? detail.ticket.priority}</Field>
            <Field label="Categoria">{detail.ticket.category ?? "—"}</Field>
            <Field label="Origem">{detail.ticket.source_system}</Field>
            <Field label="Solicitante">{detail.ticket.requester ?? "—"}</Field>
            <Field label="Concluído em">
              {detail.resolved_at ? new Date(detail.resolved_at).toLocaleString("pt-BR") : "—"}
            </Field>
          </dl>
          <p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
            {detail.ticket.description}
          </p>
        </Card>

        <Card title="Editar chamado" className="lg:col-span-2">
          <TicketEditPanel
            id={detail.workflow_execution_id}
            initialValues={{
              subject: detail.ticket.subject,
              description: detail.ticket.description,
              priority: detail.ticket.priority as TicketFormValues["priority"],
              category: detail.ticket.category ?? "",
            }}
            resolved={detail.resolved_at !== null}
          />
        </Card>

        <Card title="Linha do tempo">
          <Timeline events={detail.timeline} />
        </Card>
      </div>
    </div>
  );
}
