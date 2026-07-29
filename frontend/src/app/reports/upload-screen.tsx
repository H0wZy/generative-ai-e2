'use client'

import Link from 'next/link'
import { useActionState, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Tag, type TagTone } from '@/components/ui/tag'
import {
  commitUpload,
  detectUpload,
  type DetectedFile,
  type UploadState,
} from './actions'

const KIND_LABEL: Record<DetectedFile['kind'], string> = {
  fs_abertos: 'Chamados em aberto',
  fs_fechados: 'Chamados fechados',
  jira_cards: 'Cards do Jira',
  unknown: 'Não reconhecido — será ignorado',
  unreadable: 'Não foi possível abrir — será ignorado',
  too_large: 'Acima do limite de 20 MB — será ignorado',
}

const KIND_TONE: Record<DetectedFile['kind'], TagTone> = {
  fs_abertos: 'accent',
  fs_fechados: 'success',
  jira_cards: 'accent',
  unknown: 'neutral',
  unreadable: 'danger',
  too_large: 'danger',
}

const IGNORED: DetectedFile['kind'][] = ['unknown', 'unreadable', 'too_large']

export function UploadScreen({ hasData }: { hasData: boolean }) {
  // Two steps, no server-side state between them: the same files are sent
  // again on commit. The input is uncontrolled, so the browser keeps them.
  const formRef = useRef<HTMLFormElement>(null)
  const [fileCount, setFileCount] = useState(0)

  const [preview, previewAction, previewPending] = useActionState<
    UploadState | null,
    FormData
  >(detectUpload, null)
  const [commit, commitAction, commitPending] = useActionState<
    UploadState | null,
    FormData
  >(commitUpload, null)

  const showPreview = preview?.phase === 'preview' && commit?.phase !== 'committed'

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header>
        <h2 className="text-xl font-semibold text-text">
          {hasData ? 'Carregar novos dados' : 'Dados ainda não carregados, deseja carregar?'}
        </h2>
        <p className="mt-1 text-sm text-muted">
          Exportações do Power BI: chamados em aberto, chamados fechados e cards
          do Jira. O tipo de cada arquivo é reconhecido pelas colunas do
          cabeçalho, não pelo nome — pode enviar em qualquer ordem.
        </p>
      </header>

      <form
        ref={formRef}
        action={previewAction}
        className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-sm"
      >
        <input
          type="file"
          name="files"
          multiple
          accept=".xlsx,.csv"
          onChange={(event) => setFileCount(event.target.files?.length ?? 0)}
          className="text-sm text-text file:mr-3 file:min-h-9 file:rounded-md file:border-0 file:bg-neutral-800 file:px-3 file:text-sm file:font-medium file:text-neutral-100 hover:file:bg-neutral-700"
        />
        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" disabled={previewPending || fileCount === 0}>
            {previewPending ? 'Analisando…' : 'Pré-visualizar'}
          </Button>
          {/* Only on the voluntary path: there is nowhere to go back to on
              the mandatory first-visit screen. */}
          {hasData && (
            <Link
              href="/reports"
              className="inline-flex min-h-9 items-center rounded-md px-3 text-sm text-muted transition-colors hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              Cancelar e voltar
            </Link>
          )}
        </div>
      </form>

      {preview?.phase === 'error' && (
        <p role="alert" className="rounded-md bg-surface px-4 py-3 text-sm text-text shadow-sm">
          {preview.message}
        </p>
      )}

      {showPreview && (
        <div className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-sm">
          <div>
            <h3 className="text-sm font-semibold text-text">
              Pré-visualização — nada foi gravado ainda
            </h3>
            <p className="mt-1 text-xs text-muted">
              A contagem já é de linhas válidas: é exatamente o que será
              gravado, não o total bruto do arquivo.
            </p>
          </div>

          <ul className="flex flex-col gap-2">
            {preview.files.map((file) => (
              <li
                key={file.filename}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-divider px-3 py-2"
              >
                <span className="font-mono text-xs text-muted">
                  {file.filename}
                </span>
                <span className="flex items-center gap-3">
                  <Tag tone={KIND_TONE[file.kind]}>{KIND_LABEL[file.kind]}</Tag>
                  {!IGNORED.includes(file.kind) && (
                    <span className="tabular-nums text-xs text-muted">
                      {file.row_count} linhas
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>

          <form
            action={(formData) => {
              // Re-send the same files the preview used — the server keeps no
              // state between the two steps.
              const input = formRef.current?.querySelector<HTMLInputElement>(
                'input[type="file"]'
              )
              for (const file of input?.files ?? []) {
                formData.append('files', file, file.name)
              }
              commitAction(formData)
            }}
          >
            <Button type="submit" variant="primary" disabled={commitPending}>
              {commitPending ? 'Gravando…' : 'Confirmar e gravar'}
            </Button>
            <p className="mt-2 text-xs text-muted">
              A carga sempre mescla, nunca substitui. Reenviar os mesmos
              arquivos atualiza, não duplica.
            </p>
          </form>
        </div>
      )}

      {commit?.phase === 'committed' && (
        <div role="status" className="rounded-md bg-surface px-4 py-3 text-sm text-text shadow-sm">
          <p>
            {commit.inserted} registro(s) inserido(s), {commit.updated}{' '}
            atualizado(s).
          </p>
          {commit.skipped.length > 0 && (
            <p className="mt-1 text-muted">
              Ignorados: {commit.skipped.join(', ')}
            </p>
          )}
        </div>
      )}

      {commit?.phase === 'error' && (
        <p role="alert" className="rounded-md bg-surface px-4 py-3 text-sm text-text shadow-sm">
          {commit.message}
        </p>
      )}
    </div>
  )
}
