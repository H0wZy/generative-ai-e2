'use client'

import Link from 'next/link'
import { useActionState, useRef, useState } from 'react'
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

const KIND_STYLE: Record<DetectedFile['kind'], string> = {
  fs_abertos: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
  fs_fechados: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  jira_cards: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
  unknown: 'border-zinc-600/40 bg-zinc-600/10 text-zinc-400',
  unreadable: 'border-red-500/40 bg-red-500/10 text-red-300',
  too_large: 'border-red-500/40 bg-red-500/10 text-red-300',
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
        <h2 className="text-xl font-semibold tracking-tight">
          {hasData ? 'Carregar novos dados' : 'Dados ainda não carregados, deseja carregar?'}
        </h2>
        <p className="mt-1 text-sm text-zinc-400">
          Exportações do Power BI: chamados em aberto, chamados fechados e cards
          do Jira. O tipo de cada arquivo é reconhecido pelas colunas do
          cabeçalho, não pelo nome — pode enviar em qualquer ordem.
        </p>
      </header>

      <form
        ref={formRef}
        action={previewAction}
        className="flex flex-col gap-4 rounded-lg border border-zinc-800 bg-zinc-900 p-5"
      >
        <input
          type="file"
          name="files"
          multiple
          accept=".xlsx,.csv"
          onChange={(event) => setFileCount(event.target.files?.length ?? 0)}
          className="text-sm text-zinc-300 file:mr-3 file:rounded file:border file:border-zinc-700 file:bg-zinc-800 file:px-3 file:py-1.5 file:text-sm file:text-zinc-200 hover:file:bg-zinc-700"
        />
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={previewPending || fileCount === 0}
            className="rounded border border-sky-500/40 bg-sky-500/10 px-3 py-1.5 text-sm font-medium text-sky-300 transition-colors hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {previewPending ? 'Analisando…' : 'Pré-visualizar'}
          </button>
          {/* Only on the voluntary path: there is nowhere to go back to on
              the mandatory first-visit screen. */}
          {hasData && (
            <Link
              href="/analytics"
              className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:bg-zinc-800"
            >
              Cancelar e voltar
            </Link>
          )}
        </div>
      </form>

      {preview?.phase === 'error' && (
        <p className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {preview.message}
        </p>
      )}

      {showPreview && (
        <div className="flex flex-col gap-4 rounded-lg border border-zinc-800 bg-zinc-900 p-5">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">
              Pré-visualização — nada foi gravado ainda
            </h3>
            <p className="mt-1 text-xs text-zinc-500">
              A contagem já é de linhas válidas: é exatamente o que será
              gravado, não o total bruto do arquivo.
            </p>
          </div>

          <ul className="flex flex-col gap-2">
            {preview.files.map((file) => (
              <li
                key={file.filename}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-zinc-800 px-3 py-2"
              >
                <span className="font-mono text-xs text-zinc-300">
                  {file.filename}
                </span>
                <span className="flex items-center gap-3">
                  <span
                    className={`rounded border px-2 py-0.5 text-xs font-medium ${KIND_STYLE[file.kind]}`}
                  >
                    {KIND_LABEL[file.kind]}
                  </span>
                  {!IGNORED.includes(file.kind) && (
                    <span className="tabular-nums text-xs text-zinc-400">
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
            <button
              type="submit"
              disabled={commitPending}
              className="rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {commitPending ? 'Gravando…' : 'Confirmar e gravar'}
            </button>
            <p className="mt-2 text-xs text-zinc-500">
              A carga sempre mescla, nunca substitui. Reenviar os mesmos
              arquivos atualiza, não duplica.
            </p>
          </form>
        </div>
      )}

      {commit?.phase === 'committed' && (
        <div className="rounded border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
          <p>
            {commit.inserted} registro(s) inserido(s), {commit.updated}{' '}
            atualizado(s).
          </p>
          {commit.skipped.length > 0 && (
            <p className="mt-1 text-amber-300">
              Ignorados: {commit.skipped.join(', ')}
            </p>
          )}
        </div>
      )}

      {commit?.phase === 'error' && (
        <p className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {commit.message}
        </p>
      )}
    </div>
  )
}
