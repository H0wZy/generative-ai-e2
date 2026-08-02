import Link from "next/link";

import { Bars } from "@/components/charts/bars";
import { Donut } from "@/components/charts/donut";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Stat } from "@/components/ui/stat";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type {
  Availability,
  Metrics,
  SprintDashboard,
  WorkflowListResponse,
} from "@/lib/types";

// Cada indicador declara a janela a que se refere (FR-012). As contagens de
// /metrics são acumuladas desde o início da operação — não há corte temporal
// na origem, e inventar um seria pior que nomear o que existe.
const ITSM_WINDOW = "acumulado";

export default async function Home() {
  const [metrics, workflows, agile] = await Promise.all([
    apiFetch<Metrics>("/api/v1/metrics"),
    apiFetch<WorkflowListResponse>("/api/v1/workflows?limit=200"),
    apiFetch<Availability<SprintDashboard>>("/api/v1/agile/sprint"),
  ]);

  const open = metrics.ok ? metrics.data.pending + metrics.data.retry_scheduled : null;
  const critical = metrics.ok
    ? metrics.data.failed + metrics.data.needs_human_review
    : null;

  // Carga por squad a partir da fila real (FR-011). A distribuição por pessoa
  // depende de responsável no ticket, campo que a origem ainda não traz.
  const bySquad = new Map<string, number>();
  if (workflows.ok) {
    for (const item of workflows.data.items) {
      const squad = item.squad_id ?? "sem squad";
      bySquad.set(squad, (bySquad.get(squad) ?? 0) + 1);
    }
  }
  const squadSlices = [...bySquad.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([label, value]) => ({ label, value }));

  const sprint = agile.ok && agile.data.available ? agile.data.data : null;
  const agileReason = agile.ok && !agile.data.available ? agile.data.reason : null;
  const agileDetail = agile.ok
    ? agile.data.available
      ? null
      : agile.data.detail
    : agile.error.message;

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-text">Como está a operação hoje</h2>
          <p className="text-sm text-muted-foreground">
            Freshservice e Jira na mesma tela · janela: {ITSM_WINDOW}
          </p>
        </div>
        <Link
          href="/itsm"
          className="text-sm text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          Ver fila de tickets
        </Link>
      </header>

      {/* FR-013: a indisponibilidade de uma origem não impede as outras. */}
      <section
        aria-label="Indicadores de ITSM"
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Stat
          label="Incidentes abertos"
          value={open ?? "indisponível"}
          hint={metrics.ok ? ITSM_WINDOW : metrics.error.message}
        />
        <Stat
          label="Itens críticos"
          value={critical ?? "indisponível"}
          hint={metrics.ok ? `falhas e revisão humana · ${ITSM_WINDOW}` : metrics.error.message}
        />
        <Stat
          label="Concluídos"
          value={metrics.ok ? metrics.data.completed : "indisponível"}
          hint={metrics.ok ? ITSM_WINDOW : metrics.error.message}
        />
        {/* Nenhum campo de prazo chega do Freshservice hoje. Declarar
            indisponível é mais honesto que derivar número não auditável. */}
        <Stat
          label="Cumprimento de SLA"
          value="indisponível"
          hint="sem prazo conhecido na origem"
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Progresso do sprint">
          {sprint?.sprint ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-sm text-text">{sprint.sprint.name}</p>
                <p className="text-xs text-muted-foreground">
                  {sprint.sprint.days_left} dia(s) restante(s)
                </p>
              </div>
              <p className="text-2xl font-semibold tabular-nums text-text">
                {sprint.sprint.completed_points} / {sprint.sprint.committed_points}
                <span className="ml-1 text-sm font-normal text-muted-foreground">pontos</span>
              </p>
              <p className="text-xs text-muted-foreground">
                {sprint.sprint.start_date?.slice(0, 10)} a {sprint.sprint.end_date?.slice(0, 10)}
              </p>
            </div>
          ) : sprint ? (
            <EmptyState title="Nenhum sprint ativo" hint="O board não tem sprint em andamento." />
          ) : (
            <UnavailableState reason={agileReason ?? "unavailable"} detail={agileDetail} />
          )}
        </Card>

        <Card title="Velocidade das últimas iterações">
          {sprint && sprint.velocity.length > 0 ? (
            <Bars
              label="Pontos comprometidos e concluídos por sprint"
              seriesLabels={["Comprometido", "Concluído"]}
              groups={sprint.velocity.map((point) => ({
                label: point.sprint_name,
                values: [point.committed, point.completed],
              }))}
            />
          ) : sprint ? (
            <EmptyState
              title="Sem histórico de velocidade"
              hint="Nenhum sprint encerrado ainda neste board."
            />
          ) : (
            <UnavailableState reason={agileReason ?? "unavailable"} detail={agileDetail} />
          )}
        </Card>

        <Card title="Carga por squad">
          {workflows.ok && squadSlices.length > 0 ? (
            <Donut label="Distribuição de execuções por squad" slices={squadSlices} />
          ) : workflows.ok ? (
            <EmptyState title="Nenhuma execução na fila" />
          ) : (
            <UnavailableState reason="unavailable" detail={workflows.error.message} />
          )}
        </Card>

        <Card title="Volume por status">
          {metrics.ok ? (
            <Donut
              label="Execuções por status"
              slices={[
                { label: "Concluídos", value: metrics.data.completed },
                { label: "Pendentes", value: metrics.data.pending },
                { label: "Retry", value: metrics.data.retry_scheduled },
                { label: "Exceções", value: critical ?? 0 },
              ]}
            />
          ) : (
            <UnavailableState reason="unavailable" detail={metrics.error.message} />
          )}
        </Card>
      </div>
    </div>
  );
}
