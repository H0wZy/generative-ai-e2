import Link from 'next/link'
import { RankedBars } from '@/components/charts/ranked-bars'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Stat } from '@/components/ui/stat'
import { UnavailableState } from '@/components/ui/unavailable-state'
import { ALL_FILTER_FIELDS, type FilterOptions } from './fields'
import { FilterBar } from './filter-bar'
import { UploadScreen } from './upload-screen'

const LINK_CLASS =
  'text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus'

const API_URL = process.env.API_URL || 'http://localhost:8000'

type DataStatus = {
  hasData: boolean
  chamados: number
  cards: number
  squads: string[]
  periodo: { de: string | null; ate: string | null }
  ultimaSincronizacao: string | null
}

type Coverage = {
  best_effort: {
    total_cards: number
    com_vinculo_extraivel: number
    com_chamado_correspondente: number
    cobertura: number | null
  }
  deterministic: {
    total_tombados: number
    com_vinculo: number
    cobertura: number | null
  }
}

type Throughput = {
  total_concluidos: number
  total_cards_no_filtro: number
  por_periodo: { periodo: string; count: number }[]
  por_squad_periodo: { periodo: string; squad: string; count: number }[]
}

type Distribuicao = {
  total_ativos: number
  total_recursos: number
  media_por_recurso: number | null
  por_responsavel: { assignee: string; count: number }[]
  por_status: { status: string; count: number; ativo: boolean }[]
}

type LeadTime = {
  media_dias: number | null
  mediana_dias: number | null
  amostras: number
  distribuicao: { faixa: string; count: number }[]
  por_periodo: { periodo: string; media_dias: number }[]
}

const TABS = [
  { id: 'comparacao', label: 'Comparação' },
  { id: 'throughput', label: 'Throughput' },
  { id: 'distribuicao', label: 'Distribuição de trabalho' },
  { id: 'lead-time', label: 'Lead time' },
] as const

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/analytics/${path}`, {
      cache: 'no-store',
    })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

function queryFrom(params: Record<string, string | string[] | undefined>): string {
  const query = new URLSearchParams()
  for (const field of ALL_FILTER_FIELDS) {
    const value = params[field]
    if (typeof value === 'string' && value) query.set(field, value)
  }
  const periodicidade = params.periodicidade
  if (typeof periodicidade === 'string' && periodicidade) {
    query.set('periodicidade', periodicidade)
  }
  return query.toString()
}

export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const status = await getJson<DataStatus>('data-status')

  // The gate is checked on its own, before anything else: it is the only way
  // to decide "upload or dashboard" without depending on calls that make no
  // sense on an empty base.
  if (status === null) {
    return (
      <div className="p-4 md:p-6">
        <UnavailableState
          reason="unavailable"
          detail="Não foi possível conectar ao servidor."
        />
      </div>
    )
  }

  const wantsUpload = params.upload === '1'

  if (!status.hasData || wantsUpload) {
    return (
      <div className="p-4 md:p-6">
        <UploadScreen hasData={status.hasData} />
      </div>
    )
  }

  const query = queryFrom(params)
  const suffix = query ? `?${query}` : ''
  const activeTab =
    typeof params.tab === 'string' && TABS.some((t) => t.id === params.tab)
      ? params.tab
      : 'comparacao'

  const [options, coverage, throughput, distribuicao, leadTime] = await Promise.all([
    getJson<FilterOptions>(`filter-options${suffix}`),
    getJson<Coverage>('link-coverage'),
    getJson<Throughput>(`throughput${suffix}`),
    getJson<Distribuicao>(`distribuicao-trabalho${suffix}`),
    getJson<LeadTime>(`lead-time${suffix}`),
  ])

  const keep = new URLSearchParams(query)

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <div className="flex w-full flex-col gap-4">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-text">Reports</h2>
            <p className="text-sm text-muted">
              {status.chamados} chamados · {status.cards} cards ·{' '}
              {status.squads.length} squads · {status.periodo.de} a{' '}
              {status.periodo.ate}
            </p>
          </div>
          <Link href="/reports?upload=1" className={LINK_CLASS}>
            Carregar novos dados
          </Link>
        </header>

        <nav className="flex flex-wrap gap-2 border-b border-divider pb-2">
          {TABS.map((tab) => {
            const tabParams = new URLSearchParams(keep)
            tabParams.set('tab', tab.id)
            const active = tab.id === activeTab
            return (
              <Link
                key={tab.id}
                href={`/reports?${tabParams.toString()}`}
                aria-current={active ? 'page' : undefined}
                className={`min-h-9 rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
                  active
                    ? 'bg-accent-800 font-medium text-neutral-100'
                    : 'text-muted hover:bg-elevated hover:text-text'
                }`}
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>

        {options && (
          <FilterBar
            options={options}
            showPeriodicidade={activeTab === 'throughput' || activeTab === 'lead-time'}
          />
        )}

        {activeTab === 'comparacao' &&
          (coverage ? (
            <section className="grid gap-3 sm:grid-cols-2">
              <Card title="Antes — tombamento manual">
                <p className="text-4xl font-semibold tabular-nums text-text">
                  {coverage.best_effort.cobertura !== null
                    ? `${Math.round(coverage.best_effort.cobertura * 1000) / 10}%`
                    : '—'}
                </p>
                <p className="mt-2 text-sm text-muted">
                  {coverage.best_effort.com_chamado_correspondente} de{' '}
                  {coverage.best_effort.total_cards} cards têm vínculo utilizável.
                </p>
                <p className="mt-1 text-xs text-muted">
                  {coverage.best_effort.com_vinculo_extraivel} têm um número
                  extraível do título; o resto não cita nenhum, ou cita dois
                  números ambíguos.
                </p>
              </Card>

              <Card title="Depois — tombamento automático">
                <p className="text-4xl font-semibold tabular-nums text-text">
                  {coverage.deterministic.cobertura !== null
                    ? `${Math.round(coverage.deterministic.cobertura * 1000) / 10}%`
                    : '—'}
                </p>
                <p className="mt-2 text-sm text-muted">
                  {coverage.deterministic.com_vinculo} de{' '}
                  {coverage.deterministic.total_tombados} chamados tombados têm
                  vínculo estruturado.
                </p>
                <p className="mt-1 text-xs text-muted">
                  O identificador vai num rótulo da issue: não depende de
                  ninguém digitá-lo no título.
                </p>
              </Card>
            </section>
          ) : (
            <EmptyState title="Comparação indisponível" hint="A base não devolveu cobertura." />
          ))}

        {activeTab === 'throughput' &&
          (throughput ? (
          <section className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat
                label="Concluídos"
                value={String(throughput.total_concluidos)}
                hint='Resolution = "Done" exatamente'
              />
              <Stat
                label="Cards no filtro"
                value={String(throughput.total_cards_no_filtro)}
              />
            </div>
            <RankedBars
              rows={throughput.por_periodo.map((row) => ({
                label: row.periodo,
                count: row.count,
              }))}
              emptyLabel="Nenhum card concluído no recorte atual."
            />
          </section>
          ) : (
            <EmptyState title="Throughput indisponível" hint="A base não devolveu dados." />
          ))}

        {activeTab === 'distribuicao' &&
          (distribuicao ? (
          <section className="flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat label="Em execução" value={String(distribuicao.total_ativos)} />
              <Stat label="Responsáveis" value={String(distribuicao.total_recursos)} />
              <Stat
                label="Média por responsável"
                value={distribuicao.media_por_recurso?.toString() ?? '—'}
              />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-medium text-text">
                Por responsável (só status de execução)
              </h3>
              <RankedBars
                rows={distribuicao.por_responsavel.map((row) => ({
                  label: row.assignee,
                  count: row.count,
                }))}
                emptyLabel="Nenhum card em execução no recorte atual."
              />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-medium text-text">
                Por status — fluxo inteiro
              </h3>
              <RankedBars
                rows={distribuicao.por_status.map((row) => ({
                  label: row.status,
                  count: row.count,
                  muted: !row.ativo,
                }))}
                emptyLabel="Nenhum card com responsável no recorte atual."
              />
              <p className="mt-2 text-xs text-muted">
                Em destaque, os cinco status que contam como execução; em cinza,
                o resto do fluxo.
              </p>
            </div>
          </section>
          ) : (
            <EmptyState title="Distribuição indisponível" hint="A base não devolveu dados." />
          ))}

        {activeTab === 'lead-time' &&
          (leadTime ? (
          <section className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat
                label="Média"
                value={leadTime.media_dias !== null ? `${leadTime.media_dias} d` : '—'}
              />
              <Stat
                label="Mediana"
                value={
                  leadTime.mediana_dias !== null ? `${leadTime.mediana_dias} d` : '—'
                }
                hint="A distribuição tem cauda longa"
              />
              <Stat
                label="Chamados considerados"
                value={String(leadTime.amostras)}
                hint="Só chamados com card vinculado já terminado"
              />
            </div>
            <RankedBars
              rows={leadTime.distribuicao.map((row) => ({
                label: row.faixa,
                count: row.count,
              }))}
              emptyLabel="Nenhum chamado entregue no recorte atual."
            />
          </section>
          ) : (
            <EmptyState title="Lead time indisponível" hint="A base não devolveu dados." />
          ))}
      </div>
    </div>
  )
}
