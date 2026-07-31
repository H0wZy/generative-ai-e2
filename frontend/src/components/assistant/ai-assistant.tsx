"use client";

import { useEffect, useRef, useState } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import { PanelLeft } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { AssistantAnswer, AssistantMessage, ConversationSummary } from "@/lib/types";

import { ChatComposer } from "./chat-composer";
import { ConversationSidebar } from "./conversation-sidebar";
import { ConversationView, type Turn } from "./conversation-view";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "./v0/breadcrumb";

const ASK_TIMEOUT_MS = 30000;

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

interface ConversationMessage {
  role: "user" | "assistant";
  text: string;
  sources?: AssistantAnswer["sources"];
  ticket_context?: AssistantAnswer["ticket_context"];
}

export function AiAssistant() {
  const [turns, setTurns] = useState<Turn[]>([]);
  // Token do contexto (conversa) que está com uma pergunta em voo, ou null.
  // "pending" só é true quando esse token bate com o contexto ATUAL — assim
  // trocar de conversa esconde o indicador na hora (não pertence a essa
  // tela), e ele nunca fica preso: quando a resposta chega, o token sempre é
  // limpo, esteja o usuário olhando pra essa conversa ou não.
  const [pendingToken, setPendingToken] = useState<number | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Vazio durante SSR (getOrCreateSessionId só resolve no navegador).
  const sessionIdRef = useRef("");
  const scrollRef = useRef<HTMLDivElement>(null);
  // Os tokens de cor `v0-*` só existem dentro de `.v0-assistant` (globals.css)
  // — menus em portal (context-menu) precisam montar aqui dentro, não em
  // `document.body`, senão ficam sem cor (var() vazio fora do escopo).
  const rootRef = useRef<HTMLDivElement>(null);
  const lastQuestionRef = useRef("");
  // Incrementado sempre que o usuário troca de contexto (seleciona outra
  // conversa, ou começa uma nova) — uma resposta que ainda está em voo
  // quando isso acontece não deve mais escrever no estado ao chegar.
  const contextTokenRef = useRef(0);

  const pending = pendingToken !== null && pendingToken === contextTokenRef.current;
  const activeConversationTitle =
    conversations.find((conversation) => conversation.id === activeConversationId)?.title ||
    "Nova conversa";

  useEffect(() => {
    const sessionId = getOrCreateSessionId();
    sessionIdRef.current = sessionId;
    if (!sessionId) return;

    void apiFetch<{ conversations: ConversationSummary[] }>("/api/v1/assistant/conversations", {
      headers: { "X-Session-Id": sessionId },
    }).then((result) => {
      if (!result.ok) return;
      setConversations(result.data.conversations);
      if (result.data.conversations.length > 0) {
        void loadConversation(result.data.conversations[0].id);
      }
    });
  }, []);

  // Auto-scroll para a última mensagem conforme o conteúdo cresce.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, pending]);

  async function loadConversation(id: string) {
    contextTokenRef.current += 1;
    const result = await apiFetch<{ messages: ConversationMessage[] }>(
      `/api/v1/assistant/conversations/${id}/messages`,
      { headers: { "X-Session-Id": sessionIdRef.current } },
    );
    if (!result.ok) return;
    setTurns(
      result.data.messages.map((message): Turn =>
        message.role === "user"
          ? { kind: "user", text: message.text }
          : {
              kind: "assistant",
              answer: {
                status: "answered",
                answer: message.text,
                sources: message.sources ?? [],
                truncated_history: false,
                ticket_context: message.ticket_context ?? null,
              },
            },
      ),
    );
    setActiveConversationId(id);
    setFailure(null);
    setSidebarOpen(false);
  }

  function handleNewConversation() {
    contextTokenRef.current += 1;
    // Lazy: só cria a conversa de verdade na primeira pergunta enviada, pra
    // não sujar "Recentes" com conversas vazias de quem só clicou e desistiu.
    setActiveConversationId(null);
    setTurns([]);
    setFailure(null);
    setSidebarOpen(false);
  }

  async function ensureConversationId(): Promise<string | null> {
    if (activeConversationId) return activeConversationId;
    const result = await apiFetch<ConversationSummary>("/api/v1/assistant/conversations", {
      method: "POST",
      headers: { "X-Session-Id": sessionIdRef.current },
    });
    if (!result.ok) return null;
    setActiveConversationId(result.data.id);
    setConversations((prev) => [result.data, ...prev]);
    return result.data.id;
  }

  async function postQuestion(question: string) {
    const token = contextTokenRef.current;
    lastQuestionRef.current = question;
    setPendingToken(token);
    setFailure(null);

    // Histórico calculado a partir do estado ANTES desta pergunta — mesma
    // regra de antes: contexto vai como `history`, a pergunta atual vai
    // separada em `question`.
    const history: AssistantMessage[] = turns.flatMap<AssistantMessage>((turn) =>
      turn.kind === "user"
        ? [{ role: "user", text: turn.text }]
        : turn.answer.answer
          ? [{ role: "assistant", text: turn.answer.answer }]
          : [],
    );

    const conversationId = await ensureConversationId();

    // Timeout no cliente: o backend pode levar até assistant_timeout_seconds,
    // mas a UI não deve ficar presa além de um limite razoável sem explicar.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);
    let timedOut = false;
    controller.signal.addEventListener("abort", () => {
      timedOut = true;
    });

    const result = await apiFetch<AssistantAnswer>("/api/v1/assistant/ask", {
      method: "POST",
      headers: { "content-type": "application/json", "X-Session-Id": sessionIdRef.current },
      body: JSON.stringify({
        question,
        history: history.slice(-20),
        conversation_id: conversationId,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // Sempre limpa — nunca fica preso, mesmo se o usuário já trocou de
    // conversa (se o token não é mais o pending atual, isto é um no-op).
    setPendingToken((current) => (current === token ? null : current));

    // O usuário trocou de conversa enquanto esta resposta estava em voo —
    // ela pertence a outro contexto agora, não escreve mais em cima do que
    // está na tela.
    if (token !== contextTokenRef.current) return;

    if (!result.ok) {
      setFailure(
        timedOut
          ? "O assistente demorou demais para responder. Tente novamente."
          : result.error.message,
      );
      return;
    }
    setTurns((current) => [...current, { kind: "assistant", answer: result.data }]);

    if (conversationId) {
      // Best-effort: título (derivado da 1ª pergunta) e ordenação por
      // updated_at só existem no servidor — refaz a lista pra refletir.
      const listResult = await apiFetch<{ conversations: ConversationSummary[] }>(
        "/api/v1/assistant/conversations",
        { headers: { "X-Session-Id": sessionIdRef.current } },
      );
      if (listResult.ok) setConversations(listResult.data.conversations);
    }
  }

  async function refreshConversations() {
    const result = await apiFetch<{ conversations: ConversationSummary[] }>(
      "/api/v1/assistant/conversations",
      { headers: { "X-Session-Id": sessionIdRef.current } },
    );
    if (result.ok) setConversations(result.data.conversations);
  }

  async function handleRenameConversation(id: string, title: string) {
    const result = await apiFetch<ConversationSummary>(`/api/v1/assistant/conversations/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json", "X-Session-Id": sessionIdRef.current },
      body: JSON.stringify({ title }),
    });
    if (!result.ok) return;
    setConversations((current) =>
      current.map((conversation) => (conversation.id === id ? result.data : conversation)),
    );
  }

  async function handleToggleFavorite(id: string, next: boolean) {
    const result = await apiFetch<ConversationSummary>(`/api/v1/assistant/conversations/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json", "X-Session-Id": sessionIdRef.current },
      body: JSON.stringify({ is_favorite: next }),
    });
    if (!result.ok) return;
    // Re-busca em vez de reordenar localmente — favoritar muda a posição na
    // lista (favoritos primeiro) e o servidor já sabe a ordem certa.
    void refreshConversations();
  }

  async function handleDeleteConversation(id: string) {
    const result = await apiFetch<void>(`/api/v1/assistant/conversations/${id}`, {
      method: "DELETE",
      headers: { "X-Session-Id": sessionIdRef.current },
    });
    if (!result.ok) return;
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
    if (id === activeConversationId) handleNewConversation();
  }

  function handleSubmit(text: string) {
    setTurns((current) => [...current, { kind: "user", text }]);
    void postQuestion(text);
  }

  function handleRetry() {
    if (!lastQuestionRef.current) return;
    void postQuestion(lastQuestionRef.current);
  }

  return (
    <div
      ref={rootRef}
      className={`v0-assistant flex h-dvh bg-v0-background font-v0-sans text-v0-foreground ${geistSans.variable} ${geistMono.variable}`}
    >
      <ConversationSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewConversation={handleNewConversation}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={(id) => void loadConversation(id)}
        onRenameConversation={(id, title) => void handleRenameConversation(id, title)}
        onToggleFavorite={(id, next) => void handleToggleFavorite(id, next)}
        onDeleteConversation={(id) => void handleDeleteConversation(id)}
        portalContainerRef={rootRef}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-v0-border px-4 py-3 lg:px-6">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menu"
            className="flex size-8 items-center justify-center rounded-lg text-v0-muted-foreground transition-colors hover:bg-v0-accent hover:text-v0-foreground lg:hidden"
          >
            <PanelLeft className="size-4" />
          </button>
          <Breadcrumb className="min-w-0">
            <BreadcrumbList className="flex-nowrap">
              <BreadcrumbItem>
                <button
                  type="button"
                  onClick={handleNewConversation}
                  className="shrink-0 text-sm font-semibold text-v0-foreground transition-colors hover:text-v0-muted-foreground"
                >
                  Assistente de IA
                </button>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem className="min-w-0">
                <BreadcrumbPage className="text-sm">{activeConversationTitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>

        <div ref={scrollRef} className="v0-scrollbar-slim min-h-0 flex-1 overflow-y-auto">
          <ConversationView
            turns={turns}
            pending={pending}
            failure={failure}
            onRetry={handleRetry}
            onSuggestion={handleSubmit}
          />
        </div>

        <div className="bg-gradient-to-t from-v0-background via-v0-background to-transparent px-4 pb-5 pt-2 sm:px-6">
          <div className="mx-auto w-full max-w-[900px]">
            <ChatComposer onSubmit={handleSubmit} pending={pending} />
          </div>
        </div>
      </div>
    </div>
  );
}
