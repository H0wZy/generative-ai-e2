"use client";

import Image from "next/image";
import { AlertTriangle, RefreshCw } from "lucide-react";

import type { AssistantAnswer, AssistantStatus } from "@/lib/types";

import { Button } from "./v0/button";
import { EmptyState } from "./empty-state";
import { LoadingIndicator } from "./loading-indicator";
import { MessageBubble } from "./message-bubble";
import { MessageScrollerItem } from "@/components/ui/message-scroller";

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
  animateLastAssistant?: boolean;
}

export function ConversationView({ turns, pending, failure, onRetry, onSuggestion, animateLastAssistant = true }: ConversationViewProps) {
  // Ícone só na última resposta do modelo (igual claude.ai) — mensagens
  // anteriores ficam sem avatar repetido.
  const lastAssistantIndex = turns.reduce(
    (last, turn, index) => (turn.kind === "assistant" ? index : last),
    -1,
  );

  // Sem `scrollToEnd` aqui de propósito. Ele existia para compensar o colapso
  // de altura do typewriter, e disputava com a âncora da pergunta. Agora que a
  // resposta nasce com a altura final reservada (TypewriterMessage), a âncora
  // do rolador já entrega o comportamento certo: pergunta fixa no topo,
  // resposta crescendo abaixo, sem sequestrar a rolagem de quem está lendo.

  if (turns.length === 0 && !pending && !failure) {
    return <EmptyState onSuggestion={onSuggestion} />;
  }

  return (
    <>
      {turns.map((turn, index) => {
        if (turn.kind === "user") {
          return (
            <MessageScrollerItem key={index} messageId={`turn-${index}`} scrollAnchor>
              <MessageBubble role="user" text={turn.text} />
            </MessageScrollerItem>
          );
        }

        const isLastAssistant = index === lastAssistantIndex;
        const hoverMessage =
          SIGNATURE_HOVER_MESSAGES[
            (turn.answer.answer ?? "").length % SIGNATURE_HOVER_MESSAGES.length
          ];

        return (
          <MessageScrollerItem key={index} messageId={`turn-${index}`}>
            <div className="flex flex-col gap-1.5">
              <MessageBubble
                role="assistant"
                text={turn.answer.answer ?? ""}
                sources={turn.answer.sources}
                ticketContext={turn.answer.ticket_context}
                animate={isLastAssistant && animateLastAssistant}
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
          </MessageScrollerItem>
        );
      })}

      {/* Sempre montado, mesmo vazio — de propósito.
          Se este item aparecesse só com `pending`, ele sairia no MESMO commit
          em que a resposta entra, e a contagem de filhos do scroller ficaria
          IGUAL (um sai, um entra). Nesse empate a lib entra no ramo
          "mesma quantidade" e rola para a primeira âncora que ainda não está
          no conjunto de âncoras já tratadas — que, numa conversa carregada do
          histórico, é a primeira pergunta. Daí o salto para o topo medido em
          specs/006 (scrollTop 5012 → 106 no mesmo quadro em que o indicador
          some). Mantendo o item montado, toda mudança vira acréscimo puro e
          esse ramo nunca dispara.
          `contentVisibility: visible` anula o `contain-intrinsic-size` do item
          para que, vazio, ele ocupe 0px de verdade. */}
      <MessageScrollerItem messageId="loading" style={{ contentVisibility: "visible" }}>
        {pending && <LoadingIndicator />}
      </MessageScrollerItem>

      {failure && (
        <MessageScrollerItem messageId="failure">
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-v0-destructive/40 bg-v0-destructive/10 p-4"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-v0-destructive" />
            <div className="flex-1 space-y-2">
              <p className="text-sm text-v0-foreground">{failure}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="h-auto rounded-lg bg-v0-card px-3 py-1.5 text-xs"
              >
                <RefreshCw className="size-3.5" />
                Tentar novamente
              </Button>
            </div>
          </div>
        </MessageScrollerItem>
      )}
    </>
  );
}
