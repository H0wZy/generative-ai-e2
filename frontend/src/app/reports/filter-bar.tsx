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
      <span className="text-xs text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(field, event.target.value)}
        className="min-h-9 rounded-md border border-divider bg-surface px-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
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
      <details open className="rounded-lg bg-surface p-4 shadow-sm">
        <summary className="cursor-pointer text-sm font-medium text-text">
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

      <details className="rounded-lg bg-surface p-4 shadow-sm">
        <summary className="cursor-pointer text-sm font-medium text-text">
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
            <span className="text-xs text-muted">
              Periodicidade (agrupamento, não filtro)
            </span>
            <select
              value={params.get('periodicidade') ?? 'mes'}
              onChange={(event) => setParam('periodicidade', event.target.value)}
              className="min-h-9 rounded-md border border-divider bg-surface px-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
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
          className="inline-flex min-h-9 items-center rounded-md bg-neutral-800 px-3 text-sm font-medium text-neutral-100 transition-colors hover:bg-neutral-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:pointer-events-none disabled:opacity-50"
        >
          Limpar filtros{activeCount > 0 ? ` (${activeCount})` : ''}
        </button>
      </div>

      <p className="text-xs text-muted">
        As opções estreitam dentro de cada base, não entre elas: ~73% dos
        chamados não têm card, e uma cascata cruzada os faria sumir do dropdown.
      </p>
    </div>
  )
}
