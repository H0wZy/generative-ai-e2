"use client";

import Image from "next/image";
import { AlertTriangle, RefreshCw } from "lucide-react";

import type { AssistantAnswer, AssistantStatus } from "@/lib/types";

import { EmptyState } from "./empty-state";
import { LoadingIndicator } from "./loading-indicator";
import { MessageBubble } from "./message-bubble";

export type Turn = { kind: "user"; text: string } | { kind: "assistant"; answer: AssistantAnswer };

const STATUS_NOTICE: Record<Exclude<AssistantStatus, "answered">, string> = {
  rate_limited:
    "O provedor do modelo atingiu o limite de requisições. Os trechos recuperados estão abaixo.",
  unavailable: "O provedor do modelo não respondeu. Os trechos recuperados estão abaixo.",
  timeout: "O provedor do modelo demorou demais para responder. Os trechos recuperados estão abaixo.",
  disabled: "O assistente está desligado nesta instalação.",
};

// Assinatura descontraída no hover do ícone abaixo da última resposta —
// determinístico (não Math.random) pra não violar a regra de pureza de
// render dos hooks.
const SIGNATURE_HOVER_MESSAGES = [
  "Oi de novo! Bora pra próxima?",
  "Por aqui, prontinho pra ajudar.",
  "Seu assistente de plantão.",
  "Ainda te acompanhando por aqui.",
];

interface ConversationViewProps {
  turns: Turn[];
  pending: boolean;
  failure: string | null;
  onRetry: () => void;
  onSuggestion: (text: string) => void;
}

export function ConversationView({ turns, pending, failure, onRetry, onSuggestion }: ConversationViewProps) {
  if (turns.length === 0 && !pending && !failure) {
    return <EmptyState onSuggestion={onSuggestion} />;
  }

  // Ícone só na última resposta do modelo (igual claude.ai) — mensagens
  // anteriores ficam sem avatar repetido.
  const lastAssistantIndex = turns.reduce(
    (last, turn, index) => (turn.kind === "assistant" ? index : last),
    -1,
  );

  return (
    <div className="mx-auto w-full max-w-[900px] px-4 py-8 sm:px-6">
      <div className="space-y-7">
        {turns.map((turn, index) => {
          if (turn.kind === "user") {
            return <MessageBubble key={index} role="user" text={turn.text} />;
          }

          const isLastAssistant = index === lastAssistantIndex;
          const hoverMessage =
            SIGNATURE_HOVER_MESSAGES[
              (turn.answer.answer ?? "").length % SIGNATURE_HOVER_MESSAGES.length
            ];

          return (
            <div key={index} className="flex flex-col gap-1.5">
              <MessageBubble
                role="assistant"
                text={turn.answer.answer ?? ""}
                sources={turn.answer.sources}
                ticketContext={turn.answer.ticket_context}
              />
              {turn.answer.status !== "answered" && (
                <p className="text-xs text-v0-muted-foreground">{STATUS_NOTICE[turn.answer.status]}</p>
              )}
              {isLastAssistant && (
                <div
                  title={hoverMessage}
                  className="mt-4 flex size-7 shrink-0 items-center justify-center opacity-90 transition-all ease-in-out duration-200 hover:scale-120 hover:opacity-100"
                >
                  <Image src="/Claude_AI_symbol.webp" alt="Assistente de IA" width={32} height={32} />
                </div>
              )}
            </div>
          );
        })}

        {pending && <LoadingIndicator />}

        {failure && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-v0-destructive/40 bg-v0-destructive/10 p-4"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-v0-destructive" />
            <div className="flex-1 space-y-2">
              <p className="text-sm text-v0-foreground">{failure}</p>
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 rounded-lg border border-v0-border bg-v0-card px-3 py-1.5 text-xs font-medium text-v0-foreground transition-colors hover:bg-v0-accent"
              >
                <RefreshCw className="size-3.5" />
                Tentar novamente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
