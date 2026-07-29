'use server'

import { revalidatePath } from 'next/cache'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export type ReprocessState = {
  status: 'success' | 'conflict' | 'not_found' | 'error'
  message: string
}

export async function reprocessWorkflow(
  _prev: ReprocessState | null,
  formData: FormData
): Promise<ReprocessState> {
  const id = formData.get('id')
  if (typeof id !== 'string' || !id) {
    return { status: 'error', message: 'ID do workflow ausente.' }
  }

  let res: Response
  try {
    res = await fetch(`${API_URL}/api/v1/workflows/${id}/reprocess`, {
      method: 'POST',
      cache: 'no-store',
    })
  } catch {
    return {
      status: 'error',
      message: 'Não foi possível contatar a API para reprocessar.',
    }
  }

  if (res.status === 404) {
    return { status: 'not_found', message: `Workflow ${id} não encontrado.` }
  }

  if (res.status === 409) {
    const body = await res.json().catch(() => null)
    if (body?.reason === 'not_eligible') {
      return {
        status: 'conflict',
        message: `Workflow não está em estado reprocessável (status atual: ${body?.status ?? 'desconhecido'}). Correlation id: ${id}`,
      }
    }
    if (body?.reason === 'already_linked') {
      const key = body?.jira_issue_key ?? '—'
      return {
        status: 'conflict',
        message: `Já existe issue Jira para este ticket: ${key}. Correlation id: ${id}`,
      }
    }
    return {
      status: 'conflict',
      message: `Reprocessamento recusado (status atual: ${body?.status ?? 'desconhecido'}). Correlation id: ${id}`,
    }
  }

  if (!res.ok) {
    return {
      status: 'error',
      message: `Erro inesperado da API ao reprocessar (HTTP ${res.status}).`,
    }
  }

  const body = await res.json().catch(() => null)
  revalidatePath('/itsm')
  return {
    status: 'success',
    message: `Reprocessamento agendado. Correlation id: ${body?.workflow_execution_id ?? id}`,
  }
}
