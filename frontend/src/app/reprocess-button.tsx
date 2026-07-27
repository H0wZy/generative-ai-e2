'use client'

import { useActionState } from 'react'
import { reprocessWorkflow, type ReprocessState } from './actions'

const MESSAGE_STYLE: Record<ReprocessState['status'], string> = {
  success: 'text-emerald-400',
  conflict: 'text-amber-400',
  not_found: 'text-red-400',
  error: 'text-red-400',
}

export function ReprocessButton({ id }: { id: string }) {
  const [state, formAction, isPending] = useActionState<
    ReprocessState | null,
    FormData
  >(reprocessWorkflow, null)

  return (
    <div className="flex flex-col items-start gap-1">
      <form
        action={formAction}
        onSubmit={(event) => {
          const confirmed = window.confirm(
            `Reprocessar o workflow ${id}? A ação é idempotente e não cria uma nova issue Jira.`
          )
          if (!confirmed) event.preventDefault()
        }}
      >
        <input type="hidden" name="id" value={id} />
        <button
          type="submit"
          disabled={isPending}
          className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? 'Reprocessando…' : 'Reprocessar'}
        </button>
      </form>
      {state && (
        <p className={`max-w-52 text-xs ${MESSAGE_STYLE[state.status]}`}>
          {state.message}
        </p>
      )}
    </div>
  )
}
