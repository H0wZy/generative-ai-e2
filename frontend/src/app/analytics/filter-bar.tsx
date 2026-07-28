'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect } from 'react'
import {
  ALL_FILTER_FIELDS,
  FRESHSERVICE_FIELDS,
  JIRA_FIELDS,
  PERIODICIDADES,
  type FilterOptions,
} from './fields'

function Select({
  field,
  label,
  options,
  value,
  onChange,
}: {
  field: string
  label: string
  options: string[]
  value: string
  onChange: (field: string, value: string) => void
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-zinc-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(field, event.target.value)}
        className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200"
      >
        <option value="">Todos</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export function FilterBar({
  options,
  showPeriodicidade,
}: {
  options: FilterOptions
  showPeriodicidade: boolean
}) {
  const router = useRouter()
  const params = useSearchParams()

  const setParam = (field: string, value: string) => {
    const next = new URLSearchParams(params.toString())
    if (value) next.set(field, value)
    else next.delete(field)
    router.replace(`?${next.toString()}`)
  }

  // With the cascade, a selected value can stop existing once another filter
  // of the same group changes. Left alone, the <select> would show a value
  // that is no longer in its own list, which reads as broken.
  useEffect(() => {
    const stale = ALL_FILTER_FIELDS.filter((field) => {
      const current = params.get(field)
      return current && !(options[field] ?? []).includes(current)
    })
    if (stale.length === 0) return

    const next = new URLSearchParams(params.toString())
    for (const field of stale) next.delete(field)
    router.replace(`?${next.toString()}`)
  }, [options, params, router])

  const activeCount = ALL_FILTER_FIELDS.filter((f) => params.get(f)).length

  return (
    <div className="flex flex-col gap-3">
      <details open className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
        <summary className="cursor-pointer text-sm font-medium text-zinc-300">
          Freshservice — chamado ({FRESHSERVICE_FIELDS.length} campos)
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {FRESHSERVICE_FIELDS.map(({ field, label }) => (
            <Select
              key={field}
              field={field}
              label={label}
              options={options[field] ?? []}
              value={params.get(field) ?? ''}
              onChange={setParam}
            />
          ))}
        </div>
      </details>

      <details className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
        <summary className="cursor-pointer text-sm font-medium text-zinc-300">
          Jira — card ({JIRA_FIELDS.length} campos)
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {JIRA_FIELDS.map(({ field, label }) => (
            <Select
              key={field}
              field={field}
              label={label}
              options={options[field] ?? []}
              value={params.get(field) ?? ''}
              onChange={setParam}
            />
          ))}
        </div>
      </details>

      <div className="flex flex-wrap items-end gap-4">
        {showPeriodicidade && (
          <label className="flex flex-col gap-1">
            <span className="text-xs text-zinc-500">
              Periodicidade (agrupamento, não filtro)
            </span>
            <select
              value={params.get('periodicidade') ?? 'mes'}
              onChange={(event) => setParam('periodicidade', event.target.value)}
              className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200"
            >
              {PERIODICIDADES.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        )}

        <button
          type="button"
          disabled={activeCount === 0}
          onClick={() => {
            const next = new URLSearchParams(params.toString())
            for (const field of ALL_FILTER_FIELDS) next.delete(field)
            router.replace(`?${next.toString()}`)
          }}
          className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Limpar filtros{activeCount > 0 ? ` (${activeCount})` : ''}
        </button>
      </div>

      <p className="text-xs text-zinc-600">
        As opções estreitam dentro de cada base, não entre elas: ~73% dos
        chamados não têm card, e uma cascata cruzada os faria sumir do dropdown.
      </p>
    </div>
  )
}
