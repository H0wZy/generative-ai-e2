"use client";

import type { RetrievedSource, TicketRefSource } from "@/lib/types";

import { MarkdownMessage } from "./markdown-message";
import { SourceAccordion } from "./source-accordion";

interface MessageBubbleProps {
  role: "user" | "assistant";
  text: string;
  sources?: RetrievedSource[];
  ticketContext?: TicketRefSource | null;
}

export function MessageBubble({ role, text, sources = [], ticketContext = null }: MessageBubbleProps) {
  if (role === "user") {
    return (
      <div className="v0-animate-message-in flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-v0-accent px-4 py-2.5 text-pretty text-sm leading-relaxed text-v0-foreground">
          <p className="whitespace-pre-wrap">{text}</p>
        </div>
      </div>
    );
  }

  // Sem avatar à esquerda — igual claude.ai, a resposta ocupa a largura toda;
  // a marca do assistente vira uma assinatura abaixo (ConversationView).
  return (
    <div className="v0-animate-message-in min-w-0">
      {text ? <MarkdownMessage content={text} /> : null}
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
  );
}
