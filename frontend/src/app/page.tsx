import Link from 'next/link'
import { ReprocessButton } from './reprocess-button'

const API_URL = process.env.API_URL || 'http://localhost:8000'

type WorkflowStatus =
  | 'pending'
  | 'processing'
  | 'retry_scheduled'
  | 'completed'
  | 'failed'
  | 'needs_human_review'

type WorkflowItem = {
  workflow_execution_id: string
  status: WorkflowStatus
  attempt_count: number
  squad_id: string | null
  routing_confidence: number | null
  jira_issue_key: string | null
  ticket: {
    source_ticket_id: string
    subject: string
    category: string
  }
}

type Metrics = {
  received: number | null
  pending: number | null
  completed: number | null
  retry_scheduled: number | null
  failed: number | null
  needs_human_review: number | null
  duplicates_avoided: number | null
}

const METRIC_CARDS: { key: keyof Metrics; label: string }[] = [
  { key: 'received', label: 'Recebidos' },
  { key: 'completed', label: 'Concluídos' },
  { key: 'failed', label: 'Falhas' },
  { key: 'retry_scheduled', label: 'Retry agendado' },
  { key: 'needs_human_review', label: 'Revisão humana' },
  { key: 'pending', label: 'Pendentes' },
  { key: 'duplicates_avoided', label: 'Duplicidades evitadas' },
]

const STATUS_STYLE: Record<
  WorkflowStatus,
  { label: string; badge: string; row: string }
> = {
  pending: {
    label: 'Pendente',
    badge: 'border-zinc-500/40 bg-zinc-500/10 text-zinc-300',
    row: '',
  },
  processing: {
    label: 'Processando',
    badge: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
    row: '',
  },
  completed: {
    label: 'Concluído',
    badge: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
    row: '',
  },
  retry_scheduled: {
    label: 'Retry agendado',
    badge: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
    row: 'border-l-2 border-l-amber-500 bg-amber-500/5',
  },
  failed: {
    label: 'Falha',
    badge: 'border-red-500/40 bg-red-500/10 text-red-300',
    row: 'border-l-2 border-l-red-500 bg-red-500/5',
  },
  needs_human_review: {
    label: 'Revisão humana',
    badge: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
    row: 'border-l-2 border-l-violet-500 bg-violet-500/5',
  },
}

const REPROCESS_ELIGIBLE: WorkflowStatus[] = ['failed', 'needs_human_review']

async function getMetrics(): Promise<{
  data: Metrics | null
  error: string | null
}> {
  try {
    const res = await fetch(`${API_URL}/api/v1/metrics`, { cache: 'no-store' })
    if (!res.ok) {
      return { data: null, error: `API respondeu HTTP ${res.status} em /metrics.` }
    }
    return { data: await res.json(), error: null }
  } catch {
    return {
      data: null,
      error: 'Não foi possível conectar à API para carregar as métricas.',
    }
  }
}

async function getWorkflows(): Promise<{
  data: WorkflowItem[] | null
  error: string | null
}> {
  try {
    const res = await fetch(`${API_URL}/api/v1/workflows?limit=50`, {
      cache: 'no-store',
    })
    if (!res.ok) {
      return { data: null, error: `API respondeu HTTP ${res.status} em /workflows.` }
    }
    const body = await res.json()
    return { data: body.items ?? [], error: null }
  } catch {
    return {
      data: null,
      error: 'Não foi possível conectar à API para carregar os workflows.',
    }
  }
}

export default async function Home() {
  const [metrics, workflows] = await Promise.all([getMetrics(), getWorkflows()])

  return (
    <div className="flex flex-1 flex-col bg-zinc-950 px-6 py-10 text-zinc-100 sm:px-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Painel de operação
            </h1>
            <p className="text-sm text-zinc-400">
              Freshservice → Jira · execuções e exceções
            </p>
          </div>
          <Link
            href="/analytics"
            className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
          >
            Painel analítico
          </Link>
        </header>

        <section aria-label="Métricas">
          {metrics.error ? (
            <p className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {metrics.error}
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {METRIC_CARDS.filter(({ key }) => metrics.data?.[key] !== null).map(
                ({ key, label }) => (
                  <div
                    key={key}
                    className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3"
                  >
                    <p className="text-xs text-zinc-400">{label}</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums">
                      {metrics.data?.[key]}
                    </p>
                  </div>
                )
              )}
            </div>
          )}
        </section>

        <section aria-label="Workflows">
          {workflows.error ? (
            <p className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {workflows.error}
            </p>
          ) : workflows.data && workflows.data.length === 0 ? (
            <p className="rounded border border-zinc-800 bg-zinc-900 px-4 py-6 text-center text-sm text-zinc-400">
              Nenhum workflow encontrado.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-zinc-800">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-800 bg-zinc-900 text-xs uppercase text-zinc-400">
                  <tr>
                    <th className="px-3 py-2 font-medium">Ticket</th>
                    <th className="px-3 py-2 font-medium">Assunto</th>
                    <th className="px-3 py-2 font-medium">Categoria</th>
                    <th className="px-3 py-2 font-medium">Squad</th>
                    <th className="px-3 py-2 font-medium">Confiança</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Tentativas</th>
                    <th className="px-3 py-2 font-medium">Issue Jira</th>
                    <th className="px-3 py-2 font-medium">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {workflows.data?.map((item) => {
                    const style = STATUS_STYLE[item.status]
                    return (
                      <tr key={item.workflow_execution_id} className={style.row}>
                        <td className="px-3 py-2 font-mono text-xs text-zinc-300">
                          {item.ticket.source_ticket_id}
                        </td>
                        <td className="px-3 py-2 text-zinc-200">
                          {item.ticket.subject}
                        </td>
                        <td className="px-3 py-2 text-zinc-400">
                          {item.ticket.category}
                        </td>
                        <td className="px-3 py-2 text-zinc-400">
                          {item.squad_id ?? '—'}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-zinc-400">
                          {item.routing_confidence !== null
                            ? `${Math.round(item.routing_confidence * 100)}%`
                            : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${style.badge}`}
                          >
                            {style.label}
                          </span>
                        </td>
                        <td className="px-3 py-2 tabular-nums text-zinc-400">
                          {item.attempt_count}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-zinc-300">
                          {item.jira_issue_key ?? '—'}
                        </td>
                        <td className="px-3 py-2">
                          {REPROCESS_ELIGIBLE.includes(item.status) && (
                            <ReprocessButton id={item.workflow_execution_id} />
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
