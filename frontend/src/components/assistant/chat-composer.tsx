"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, Mic, Paperclip } from "lucide-react";

import { cn } from "@/lib/utils";
import type { AttachmentSummary } from "@/lib/types";
import { Button } from "./v0/button";
import { Textarea } from "./v0/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AttachmentCard } from "./attachment-card";

// Formatos aceitos nesta rodada (specs/013): .md/.txt desde o início (US1),
// .pdf entra depois que o backend passa a extrair/OCR (US3/T029) — como as
// duas chegam juntas aqui, o input já aceita os três.
const ACCEPTED_EXTENSIONS = ".md,.txt,.pdf";

const SUGGESTIONS = [
  "Como funciona a idempotência do worker?",
  "Qual é o SLA padrão para incidentes críticos?",
  "Como movo um item do backlog para a sprint atual?",
  "Qual a diferença entre o quadro Scrum e o Kanban?",
  "O que acontece quando um worker falha no meio do processamento?",
];

const ROTATION_MS = 3500;

export function ChatComposer({
  onSubmit,
  pending,
  attachment = null,
  attachmentPending = false,
  attachmentError = null,
  conversationId,
  sessionId,
  onAttach,
  onRemoveAttachment,
}: {
  onSubmit: (value: string) => void;
  pending: boolean;
  attachment?: AttachmentSummary | null;
  attachmentPending?: boolean;
  attachmentError?: string | null;
  // Só existem de fato depois do 1º upload (que já cria a conversa) —
  // por isso o card só renderiza quando `attachment` também está presente.
  conversationId?: string | null;
  sessionId?: string;
  onAttach?: (file: File) => void;
  onRemoveAttachment?: () => void;
}) {
  const [value, setValue] = useState("");
  const [suggestionIndex, setSuggestionIndex] = useState(0);
  const [showEmptyError, setShowEmptyError] = useState(false);
  const [focused, setFocused] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const errorTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isEmpty = value.trim().length === 0;

  // Rotação automática das sugestões — pausa enquanto houver conteúdo.
  useEffect(() => {
    if (!isEmpty) return;
    const interval = setInterval(() => {
      setSuggestionIndex((prev) => (prev + 1) % SUGGESTIONS.length);
    }, ROTATION_MS);
    return () => clearInterval(interval);
  }, [isEmpty]);

  // Auto-resize do textarea.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [value]);

  useEffect(() => {
    return () => {
      if (errorTimeout.current) clearTimeout(errorTimeout.current);
    };
  }, []);

  function flashEmptyError() {
    setShowEmptyError(true);
    if (errorTimeout.current) clearTimeout(errorTimeout.current);
    errorTimeout.current = setTimeout(() => setShowEmptyError(false), 2500);
  }

  function handleSubmit() {
    if (pending) return;
    if (isEmpty) {
      flashEmptyError();
      textareaRef.current?.focus();
      return;
    }
    onSubmit(value.trim());
    setValue("");
    setShowEmptyError(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Tab com campo vazio preenche a sugestão atual (autocompletar).
    // preventDefault SOMENTE quando vazio, para não quebrar a navegação por teclado.
    if (e.key === "Tab" && !e.shiftKey && isEmpty) {
      e.preventDefault();
      const suggestion = SUGGESTIONS[suggestionIndex];
      setValue(suggestion);
      requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (el) {
          el.focus();
          el.setSelectionRange(suggestion.length, suggestion.length);
        }
      });
      return;
    }

    // Enter envia; Shift+Enter quebra linha. Respeita composição de IMEs (CJK).
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleAttachClick() {
    if (attachmentPending) return;
    fileInputRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // permite escolher o mesmo arquivo de novo depois de remover
    if (file && onAttach) onAttach(file);
  }

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={handleFileChange}
        className="hidden"
        aria-hidden
      />

      {attachment && conversationId && (
        <AttachmentCard
          attachment={attachment}
          conversationId={conversationId}
          sessionId={sessionId ?? ""}
          className="mb-2 w-full max-w-full"
          onRemove={() => setConfirmRemove(true)}
        />
      )}

      {attachmentError && (
        <p role="alert" className="mb-2 text-xs text-v0-destructive">
          {attachmentError}
        </p>
      )}

      <AlertDialog open={confirmRemove} onOpenChange={setConfirmRemove}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Remover “{attachment?.file_name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              O documento deixa de valer como fonte para esta conversa. A ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                setConfirmRemove(false);
                onRemoveAttachment?.();
              }}
            >
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div
        className={cn(
          "rounded-3xl border bg-v0-card p-2.5 shadow-lg shadow-black/20 transition-colors",
          showEmptyError
            ? "border-v0-destructive"
            : focused
              ? "border-v0-ring"
              : "border-v0-border",
        )}
      >
        <div className="relative px-2 pt-1.5">
          <Textarea
            ref={textareaRef}
            value={value}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onChange={(e) => {
              setValue(e.target.value);
              if (showEmptyError) setShowEmptyError(false);
            }}
            onKeyDown={handleKeyDown}
            rows={1}
            aria-label="Digite sua pergunta para o assistente"
            aria-invalid={showEmptyError}
            aria-describedby="assistant-suggestion-hint"
          />
          {/* Placeholder dinâmico animado — só aparece quando o campo está vazio. */}
          {isEmpty && (
            <div aria-hidden className="pointer-events-none absolute inset-0 flex items-start px-2 pt-1.5">
              <span
                key={suggestionIndex}
                className="animate-suggestion truncate text-[15px] leading-relaxed text-v0-muted-foreground/60"
              >
                {SUGGESTIONS[suggestionIndex]}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={attachmentPending}
              onClick={handleAttachClick}
              title="Anexar documento (.md, .txt ou .pdf)"
              aria-label={attachmentPending ? "Enviando documento…" : "Anexar documento"}
              className="rounded-xl text-v0-muted-foreground disabled:opacity-50"
            >
              {attachmentPending ? (
                <Loader2 className="size-[18px] animate-spin" />
              ) : (
                <Paperclip className="size-[18px]" />
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled
              title="Em breve"
              aria-label="Entrada por voz (em breve)"
              className="rounded-xl text-v0-muted-foreground opacity-50"
            >
              <Mic className="size-[18px]" />
            </Button>
          </div>

          <Button
            type="button"
            onClick={handleSubmit}
            disabled={pending}
            aria-label="Perguntar"
            size="icon"
            className="rounded-xl disabled:opacity-40"
          >
            <ArrowUp className="size-[18px]" />
          </Button>
        </div>
      </div>

      <div className="flex min-h-5 items-center justify-center px-1 pt-2">
        {showEmptyError ? (
          <p role="alert" className="text-xs text-v0-destructive">
            Digite uma pergunta antes de enviar.
          </p>
        ) : (
          <p id="assistant-suggestion-hint" className="text-[11px] text-v0-muted-foreground/70">
            Pressione{" "}
            <kbd className="rounded border border-v0-border bg-v0-muted px-1 font-mono text-[10px]">
              Tab
            </kbd>{" "}
            para usar a sugestão ·{" "}
            <kbd className="rounded border border-v0-border bg-v0-muted px-1 font-mono text-[10px]">
              Enter
            </kbd>{" "}
            para enviar
          </p>
        )}
      </div>
    </div>
  );
}
