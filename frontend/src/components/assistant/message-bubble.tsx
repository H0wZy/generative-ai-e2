"use client";

import { useState } from "react";

import type { AttachmentSummary, RetrievedSource, TicketRefSource } from "@/lib/types";
import { AttachmentCard } from "./attachment-card";

import { TypewriterMessage } from "./typewriter-message";
import { SourceAccordion } from "./source-accordion";

interface MessageBubbleProps {
  role: "user" | "assistant";
  text: string;
  sources?: RetrievedSource[];
  ticketContext?: TicketRefSource | null;
  animate?: boolean;
  // Só em turnos "user" (specs/013): registro de qual anexo estava ativo
  // quando ESTA mensagem foi enviada — o chip viaja com a mensagem, igual
  // claude.ai, em vez de ficar preso acima do textarea depois do envio.
  attachment?: AttachmentSummary | null;
  conversationId?: string | null;
  sessionId?: string;
}

export function MessageBubble({
  role,
  text,
  sources = [],
  ticketContext = null,
  animate = false,
  attachment = null,
  conversationId = null,
  sessionId,
}: MessageBubbleProps) {
  if (role === "user") {
    return (
      <div className="v0-animate-message-in flex flex-col items-end gap-1.5">
        {attachment && conversationId && (
          <AttachmentCard
            attachment={attachment}
            conversationId={conversationId}
            sessionId={sessionId ?? ""}
            className="max-w-[85%]"
          />
        )}
        <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-v0-accent px-4 py-2.5 text-pretty text-sm leading-relaxed text-v0-foreground">
          <p className="whitespace-pre-wrap">{text}</p>
        </div>
      </div>
    );
  }

  return <AssistantMessageBubble text={text} sources={sources} ticketContext={ticketContext} animate={animate} />;
}

// Metadados complementares (fontes, contexto de ticket) só aparecem depois
// que a resposta termina de "digitar" — mostrá-los junto com o primeiro
// quadro (antes de qualquer texto visível) dava a impressão de citação
// vindo antes da própria resposta.
function AssistantMessageBubble({
  text,
  sources,
  ticketContext,
  animate,
}: {
  text: string;
  sources: RetrievedSource[];
  ticketContext: TicketRefSource | null;
  animate: boolean;
}) {
  // Sem texto (ex.: status "unavailable" só com fontes), não há digitação
  // nenhuma pra esperar — metadados aparecem de imediato.
  const [isTyping, setIsTyping] = useState(animate && Boolean(text));
  const metadataVisible = !text || !isTyping;

  // Sem avatar à esquerda — igual claude.ai, a resposta ocupa a largura toda;
  // a marca do assistente vira uma assinatura abaixo (ConversationView).
  return (
    <div className="v0-animate-message-in min-w-0">
      {text ? <TypewriterMessage content={text} animate={animate} onTypingChange={setIsTyping} /> : null}
      {metadataVisible && (
        <div className="v0-animate-message-in">
          {ticketContext && (
            <div className="mt-3 rounded-xl border border-v0-border bg-v0-card/50 px-3.5 py-2.5 text-xs">
              <p className="font-mono text-v0-muted-foreground">{ticketContext.jira_issue_key}</p>
              {/* Conteúdo externo não confiável: texto simples (FR-045). */}
              <p className="mt-0.5 text-v0-foreground">{ticketContext.subject}</p>
              <p className="mt-0.5 text-v0-muted-foreground">
                status: {ticketContext.status}
                {ticketContext.squad_id ? ` · squad: ${ticketContext.squad_id}` : ""}
              </p>
            </div>
          )}
          <SourceAccordion sources={sources} />
        </div>
      )}
    </div>
  );
}
