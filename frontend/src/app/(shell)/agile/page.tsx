import Link from "next/link";

import { Bars } from "@/components/charts/bars";
import { Burndown } from "@/components/charts/burndown";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Stat } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { UnavailableState } from "@/components/ui/unavailable-state";
import { apiFetch } from "@/lib/api";
import type { Availability, SprintDashboard } from "@/lib/types";

const LINK_CLASS =
  "text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

export default async function AgileDashboard() {
  const result = await apiFetch<Availability<SprintDashboard>>("/api/v1/agile/sprint");

  if (!result.ok) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState reason="unavailable" detail={result.error.message} />
      </div>
    );
  }
  if (!result.data.available) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState reason={result.data.reason} detail={result.data.detail} />
      </div>
    );
  }

  const { board, sprint, burndown, velocity, blocked } = result.data.data;

  if (!sprint) {
    return (
      <div className="p-4 md:p-6">
        <Card title={board.name}>
          <EmptyState
            title="Nenhum sprint ativo"
            hint={
              <>
                Este board não tem sprint em andamento. O{" "}
                <Link href="/agile/backlog" className={LINK_CLASS}>
                  backlog
                </Link>{" "}
                continua disponível.
              </>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-text">{sprint.name}</h2>
          {/* `goal` vazio no Jira é ausência de objetivo, não objetivo vazio. */}
          <p className="text-sm text-muted-foreground">{sprint.goal ?? "Sem objetivo definido no Jira"}</p>
        </div>
        <Link href="/agile/quadro?escopo=sprint" className={LINK_CLASS}>
          Abrir quadro
        </Link>
      </header>

      <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Dias restantes"
          value={sprint.days_left}
          hint={`até ${sprint.end_date?.slice(0, 10) ?? "—"}`}
        />
        <Stat
          label="Pontos concluídos"
          value={`${sprint.completed_points} / ${sprint.committed_points}`}
          hint="sprint atual"
        />
        <Stat label="Escopo adicionado" value={sprint.scope_added_points} hint="sprint atual" />
        <Stat label="Bloqueios" value={blocked?.length ?? 0} hint="sprint atual" />
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card title="Burndown">
          {burndown ? (
            <Burndown series={burndown} />
          ) : (
            <EmptyState title="Sprint sem datas" hint="Sem início e fim não há curva." />
          )}
        </Card>

        <Card title="Velocidade">
          {velocity.length > 0 ? (
            <Bars
              label="Pontos comprometidos e concluídos por sprint"
              seriesLabels={["Comprometido", "Concluído"]}
              groups={velocity.map((point) => ({
                label: point.sprint_name,
                values: [point.committed, point.completed],
              }))}
            />
          ) : (
            <EmptyState
              title="Sem histórico de velocidade"
              hint="Nenhum sprint encerrado neste board ainda."
            />
          )}
        </Card>

        <Card title="Bloqueios" className="lg:col-span-2">
          {blocked && blocked.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {blocked.map((item) => (
                <li
                  key={item.key}
                  className="flex flex-wrap items-center gap-2 border-b border-divider pb-2 last:border-0"
                >
                  <span className="font-mono text-xs text-muted-foreground">{item.key}</span>
                  <span className="text-sm text-text">{item.title}</span>
                  <Badge variant="danger">{item.blocked_reason}</Badge>
                  {item.assignee && (
                    <span className="text-xs text-muted-foreground">{item.assignee.display_name}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Nenhum item bloqueado" />
          )}
        </Card>
      </div>
    </div>
  );
}
