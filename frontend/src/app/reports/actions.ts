'use server'

import { revalidatePath } from 'next/cache'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export type DetectedFile = {
  filename: string
  kind:
    | 'fs_abertos'
    | 'fs_fechados'
    | 'jira_cards'
    | 'unknown'
    | 'unreadable'
    | 'too_large'
  row_count: number
}

export type UploadState =
  | { phase: 'idle' }
  | { phase: 'preview'; files: DetectedFile[] }
  | { phase: 'committed'; inserted: number; updated: number; skipped: string[] }
  | { phase: 'error'; message: string }

function collectFiles(formData: FormData): File[] {
  return formData
    .getAll('files')
    .filter((entry): entry is File => entry instanceof File && entry.size > 0)
}

async function post(path: string, files: File[]): Promise<Response> {
  const body = new FormData()
  for (const file of files) body.append('files', file, file.name)
  return fetch(`${API_URL}/api/v1/analytics/${path}`, {
    method: 'POST',
    body,
    cache: 'no-store',
  })
}

export async function detectUpload(
  _prev: UploadState | null,
  formData: FormData
): Promise<UploadState> {
  const files = collectFiles(formData)
  if (files.length === 0) {
    return { phase: 'error', message: 'Selecione ao menos um arquivo.' }
  }

  try {
    const res = await post('upload/detect', files)
    if (!res.ok) {
      return { phase: 'error', message: `API respondeu HTTP ${res.status}.` }
    }
    const body = await res.json()
    return { phase: 'preview', files: body.files ?? [] }
  } catch {
    return { phase: 'error', message: 'Não foi possível contatar a API.' }
  }
}

export async function commitUpload(
  _prev: UploadState | null,
  formData: FormData
): Promise<UploadState> {
  const files = collectFiles(formData)
  if (files.length === 0) {
    return { phase: 'error', message: 'Selecione os arquivos novamente.' }
  }

  try {
    const res = await post('upload/commit', files)
    if (!res.ok) {
      return { phase: 'error', message: `API respondeu HTTP ${res.status}.` }
    }
    const body = await res.json()
    revalidatePath('/reports')
    return {
      phase: 'committed',
      inserted: body.inserted ?? 0,
      updated: body.updated ?? 0,
      skipped: body.skipped_files ?? [],
    }
  } catch {
    return { phase: 'error', message: 'Não foi possível contatar a API.' }
  }
}
