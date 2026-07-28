import Link from 'next/link'
import { ALL_FILTER_FIELDS, type FilterOptions } from './fields'
import { FilterBar } from './filter-bar'
import { UploadScreen } from './upload-screen'

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

function Stat({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
      <p className="text-xs text-zinc-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
    </div>
  )
}

function Bars({
  rows,
  emptyLabel,
}: {
  rows: { label: string; count: number; muted?: boolean }[]
  emptyLabel: string
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-zinc-500">{emptyLabel}</p>
  }
  const max = Math.max(...rows.map((r) => r.count), 1)
  return (
    <div className="flex flex-col gap-1.5">
      {rows.map((row) => (
        <div key={row.label} className="flex items-center gap-3 text-sm">
          <span className="w-44 shrink-0 truncate text-zinc-400" title={row.label}>
            {row.label}
          </span>
          <span className="h-4 flex-1 overflow-hidden rounded bg-zinc-900">
            <span
              className={`block h-full rounded ${row.muted ? 'bg-zinc-700' : 'bg-sky-600'}`}
              style={{ width: `${(row.count / max) * 100}%` }}
            />
          </span>
          <span className="w-12 shrink-0 text-right tabular-nums text-zinc-300">
            {row.count}
          </span>
        </div>
      ))}
    </div>
  )
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
      <main className="flex flex-1 flex-col items-center justify-center gap-4 bg-zinc-950 px-6 text-zinc-100">
        <p className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Não foi possível conectar ao servidor.
        </p>
        <Link
          href="/analytics"
          className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
        >
          Tentar novamente
        </Link>
      </main>
    )
  }

  const wantsUpload = params.upload === '1'

  if (!status.hasData || wantsUpload) {
    return (
      <main className="flex flex-1 flex-col bg-zinc-950 px-6 py-10 text-zinc-100 sm:px-10">
        <UploadScreen hasData={status.hasData} />
      </main>
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
    <main className="flex flex-1 flex-col bg-zinc-950 px-6 py-10 text-zinc-100 sm:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Painel analítico
            </h1>
            <p className="text-sm text-zinc-400">
              {status.chamados} chamados · {status.cards} cards ·{' '}
              {status.squads.length} squads · {status.periodo.de} a{' '}
              {status.periodo.ate}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/"
              className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              Fila de exceções
            </Link>
            <Link
              href="/analytics?upload=1"
              className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              Carregar novos dados
            </Link>
          </div>
        </header>

        <nav className="flex flex-wrap gap-2 border-b border-zinc-800 pb-2">
          {TABS.map((tab) => {
            const tabParams = new URLSearchParams(keep)
            tabParams.set('tab', tab.id)
            const active = tab.id === activeTab
            return (
              <Link
                key={tab.id}
                href={`/analytics?${tabParams.toString()}`}
                className={`rounded px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'bg-zinc-800 font-medium text-zinc-100'
                    : 'text-zinc-400 hover:bg-zinc-900'
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

        {activeTab === 'comparacao' && coverage && (
          <section className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-5 py-4">
                <p className="text-xs uppercase tracking-wide text-amber-400">
                  Antes — tombamento manual
                </p>
                <p className="mt-2 text-4xl font-semibold tabular-nums">
                  {coverage.best_effort.cobertura !== null
                    ? `${Math.round(coverage.best_effort.cobertura * 1000) / 10}%`
                    : '—'}
                </p>
                <p className="mt-2 text-sm text-zinc-400">
                  {coverage.best_effort.com_chamado_correspondente} de{' '}
                  {coverage.best_effort.total_cards} cards têm vínculo utilizável.
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {coverage.best_effort.com_vinculo_extraivel} têm um número
                  extraível do título; o resto não cita nenhum, ou cita dois
                  números ambíguos.
                </p>
              </div>

              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-5 py-4">
                <p className="text-xs uppercase tracking-wide text-emerald-400">
                  Depois — tombamento automático
                </p>
                <p className="mt-2 text-4xl font-semibold tabular-nums">
                  {coverage.deterministic.cobertura !== null
                    ? `${Math.round(coverage.deterministic.cobertura * 1000) / 10}%`
                    : '—'}
                </p>
                <p className="mt-2 text-sm text-zinc-400">
                  {coverage.deterministic.com_vinculo} de{' '}
                  {coverage.deterministic.total_tombados} chamados tombados têm
                  vínculo estruturado.
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  O identificador vai num rótulo da issue: não depende de
                  ninguém digitá-lo no título.
                </p>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'throughput' && throughput && (
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
            <Bars
              rows={throughput.por_periodo.map((row) => ({
                label: row.periodo,
                count: row.count,
              }))}
              emptyLabel="Nenhum card concluído no recorte atual."
            />
          </section>
        )}

        {activeTab === 'distribuicao' && distribuicao && (
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
              <h3 className="mb-2 text-sm font-medium text-zinc-300">
                Por responsável (só status de execução)
              </h3>
              <Bars
                rows={distribuicao.por_responsavel.map((row) => ({
                  label: row.assignee,
                  count: row.count,
                }))}
                emptyLabel="Nenhum card em execução no recorte atual."
              />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-medium text-zinc-300">
                Por status — fluxo inteiro
              </h3>
              <Bars
                rows={distribuicao.por_status.map((row) => ({
                  label: row.status,
                  count: row.count,
                  muted: !row.ativo,
                }))}
                emptyLabel="Nenhum card com responsável no recorte atual."
              />
              <p className="mt-2 text-xs text-zinc-600">
                Em azul, os cinco status que contam como execução; em cinza, o
                resto do fluxo.
              </p>
            </div>
          </section>
        )}

        {activeTab === 'lead-time' && leadTime && (
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
            <Bars
              rows={leadTime.distribuicao.map((row) => ({
                label: row.faixa,
                count: row.count,
              }))}
              emptyLabel="Nenhum chamado entregue no recorte atual."
            />
          </section>
        )}
      </div>
    </main>
  )
}
