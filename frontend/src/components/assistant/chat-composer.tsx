"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Mic, Paperclip } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "./v0/button";
import { Textarea } from "./v0/textarea";

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
}: {
  onSubmit: (value: string) => void;
  pending: boolean;
}) {
  const [value, setValue] = useState("");
  const [suggestionIndex, setSuggestionIndex] = useState(0);
  const [showEmptyError, setShowEmptyError] = useState(false);
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
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

  return (
    <div className="w-full">
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
              disabled
              title="Em breve"
              aria-label="Anexar arquivo (em breve)"
              className="rounded-xl text-v0-muted-foreground opacity-50"
            >
              <Paperclip className="size-[18px]" />
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
