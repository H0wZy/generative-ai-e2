"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Geist, Geist_Mono } from "next/font/google";
import { PanelLeft } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import { useConversations } from "@/lib/use-conversations";
import type { AssistantAnswer, AssistantMessage, ConversationSummary } from "@/lib/types";
import { AppSidebar } from "@/components/shell/app-sidebar";

import { ChatComposer } from "./chat-composer";
import { ConversationView, type Turn } from "./conversation-view";
import { NotFoundState } from "./not-found-state";
import { Button } from "./v0/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "./v0/breadcrumb";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";

const ASK_TIMEOUT_MS = 30000;
// Mesma forma usada pelo redirecionamento de /assistant (specs/007 FR-007):
// identificador malformado cai direto em "não encontrada", sem requisição.
const UUID_RE = /^[0-9a-f-]{36}$/i;

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

interface ConversationMessage {
  role: "user" | "assistant";
  text: string;
  sources?: AssistantAnswer["sources"];
  ticket_context?: AssistantAnswer["ticket_context"];
}

type LoadState = "idle" | "loading" | "loaded" | "not-found";

interface AiAssistantProps {
  // `null` = conversa nova, ainda sem registro no servidor (/ai/chat).
  // string = conversa existente pedida pela rota (/ai/chat/{id}).
  conversationId: string | null;
}

export function AiAssistant({ conversationId }: AiAssistantProps) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Arquivar a conversa aberta pelo menu da sidebar (componente irmão do
  // painel) muda um dado que só o painel busca (archived_at, via GET
  // messages) — bump força o painel a remontar e buscar de novo, em vez de
  // inventar um canal de notificação entre irmãos pra um caso raro.
  const [archiveVersion, setArchiveVersion] = useState(0);
  const {
    conversations,
    refresh,
    toggleFavorite,
    archive,
    rename,
    deleteConversation,
    removeLocally,
    restoreLocally,
  } = useConversations();

  function handleNewConversation() {
    router.push("/ai/chat");
  }

  function handleRemoveLocally(id: string) {
    removeLocally(id);
    if (id === conversationId) router.push("/ai/chat");
  }

  return (
    <div
      className={`v0-assistant flex h-dvh overflow-hidden bg-v0-background font-v0-sans text-v0-foreground ${geistSans.variable} ${geistMono.variable}`}
    >
      <AppSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewConversation={handleNewConversation}
        conversations={conversations}
        activeConversationId={conversationId}
        onSelectConversation={(id) => {
          router.push(`/ai/chat/${id}`);
          setSidebarOpen(false);
        }}
        onRenameConversation={(id, title) => void rename(id, title)}
        onToggleFavorite={(id, next) => void toggleFavorite(id, next)}
        onDeleteConversation={(id) => void deleteConversation(id)}
        onRemoveLocally={handleRemoveLocally}
        onRestoreLocally={restoreLocally}
        onArchiveConversation={(id, isArchived) => {
          void archive(id, isArchived);
          if (id === conversationId) setArchiveVersion((v) => v + 1);
        }}
      />

      {/* `key` pela conversa (+ archiveVersion): trocar de conversa é montar
          um painel novo, não reaproveitar um antigo com efeito de reset. Isso
          descarta sozinho qualquer resposta em voo da conversa anterior
          (edge case specs/007: "pessoa envia pergunta e navega antes da
          resposta chegar") — a promise ainda resolve, mas os setters são do
          painel desmontado, e o React ignora update de estado de instância
          desmontada. */}
      <ConversationPane
        key={`${conversationId ?? "new"}:${archiveVersion}`}
        conversationId={conversationId}
        conversations={conversations}
        refresh={refresh}
        archive={archive}
        onOpenSidebar={() => setSidebarOpen(true)}
        onNewConversation={handleNewConversation}
      />
    </div>
  );
}

interface ConversationPaneProps {
  conversationId: string | null;
  conversations: ConversationSummary[];
  refresh: () => Promise<void>;
  archive: (id: string, isArchived: boolean) => Promise<void>;
  onOpenSidebar: () => void;
  onNewConversation: () => void;
}

function ConversationPane({
  conversationId,
  conversations,
  refresh,
  archive,
  onOpenSidebar,
  onNewConversation,
}: ConversationPaneProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [animateNext, setAnimateNext] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>(
    conversationId ? (UUID_RE.test(conversationId) ? "loading" : "not-found") : "idle",
  );
  const [archivedAt, setArchivedAt] = useState<string | null>(null);
  // Vem do GET .../messages (specs/007), não da lista compartilhada: essa
  // lista só traz conversas ativas (`state=active`), então uma conversa
  // arquivada sumiria do título se ele dependesse só dela.
  const [conversationTitle, setConversationTitle] = useState<string | null>(null);
  // Some conversas nascem já com id (URL) mas só existem de fato no servidor
  // depois da 1ª pergunta enviada nesta instância (criação preguiçosa).
  const [activeConversationId, setActiveConversationId] = useState<string | null>(conversationId);

  // Vazio durante SSR (getOrCreateSessionId só resolve no navegador).
  const sessionIdRef = useRef("");
  const lastQuestionRef = useRef("");

  const activeConversationTitle =
    loadState === "not-found"
      ? "Conversa não encontrada"
      : conversationTitle ||
        conversations.find((conversation) => conversation.id === activeConversationId)?.title ||
        "Nova conversa";

  useEffect(() => {
    sessionIdRef.current = getOrCreateSessionId();
    if (!conversationId || !UUID_RE.test(conversationId)) return;
    void (async () => {
      const result = await apiFetch<{ messages: ConversationMessage[]; conversation: ConversationSummary }>(
        `/api/v1/assistant/conversations/${conversationId}/messages`,
        { headers: { "X-Session-Id": sessionIdRef.current || getOrCreateSessionId() } },
      );
      if (!result.ok) {
        setLoadState("not-found");
        return;
      }
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
      setArchivedAt(result.data.conversation.archived_at);
      setConversationTitle(result.data.conversation.title);
      setLoadState("loaded");
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só uma vez: o id é fixo pra esta instância (remonta em vez de reagir a troca).
  }, []);

  async function ensureConversationId(): Promise<string | null> {
    if (activeConversationId) return activeConversationId;
    const result = await apiFetch<ConversationSummary>("/api/v1/assistant/conversations", {
      method: "POST",
      headers: { "X-Session-Id": sessionIdRef.current },
    });
    if (!result.ok) return null;
    setActiveConversationId(result.data.id);
    // Troca só o endereço, sem navegar: navegar de verdade remontaria este
    // painel e interromperia a resposta em andamento (specs/007 FR-006).
    // Assim que a conversa existir de verdade no servidor, a barra de
    // endereço já reflete o endereço definitivo.
    window.history.replaceState(null, "", `/ai/chat/${result.data.id}`);
    void refresh();
    return result.data.id;
  }

  async function postQuestion(question: string) {
    lastQuestionRef.current = question;
    setPending(true);
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

    const conversationIdForRequest = await ensureConversationId();

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
        conversation_id: conversationIdForRequest,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    setPending(false);

    if (!result.ok) {
      setFailure(
        timedOut
          ? "O assistente demorou demais para responder. Tente novamente."
          : result.error.message,
      );
      return;
    }
    setTurns((current) => [...current, { kind: "assistant", answer: result.data }]);
    setAnimateNext(true);

    if (conversationIdForRequest) {
      // Best-effort: título (derivado da 1ª pergunta) e ordenação por
      // updated_at só existem no servidor — refaz a lista pra refletir.
      void refresh();
    }
  }

  function handleArchiveOpenConversation(isArchived: boolean) {
    if (!activeConversationId) return;
    void archive(activeConversationId, isArchived);
    setArchivedAt(isArchived ? new Date().toISOString() : null);
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
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center gap-3 border-b border-v0-border px-4 py-3 md:px-6">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onOpenSidebar}
          aria-label="Abrir menu"
          className="size-8 text-v0-muted-foreground hover:text-v0-foreground md:hidden"
        >
          <PanelLeft className="size-4" />
        </Button>
        <Breadcrumb className="min-w-0">
          <BreadcrumbList className="flex-nowrap">
            <BreadcrumbItem>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onNewConversation}
                className="h-auto shrink-0 gap-0 rounded-none bg-transparent p-0 text-sm font-semibold text-v0-foreground hover:bg-transparent hover:text-v0-muted-foreground"
              >
                Assistente de IA
              </Button>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem className="min-w-0">
              <BreadcrumbPage className="text-sm">{activeConversationTitle}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </header>

      {archivedAt && (
        <div className="flex items-center justify-between gap-3 border-b border-v0-border bg-v0-muted/40 px-4 py-2 text-xs text-v0-muted-foreground md:px-6">
          <span>Esta conversa está arquivada.</span>
          <Button type="button" variant="outline" size="sm" onClick={() => handleArchiveOpenConversation(false)}>
            Desarquivar
          </Button>
        </div>
      )}

      {loadState === "not-found" ? (
        <NotFoundState onNewConversation={onNewConversation} />
      ) : loadState === "loading" ? (
        <div className="flex min-h-0 flex-1 items-center justify-center text-sm text-v0-muted-foreground">
          Carregando…
        </div>
      ) : (
        <>
          <MessageScrollerProvider autoScroll defaultScrollPosition="last-anchor" scrollPreviousItemPeek={64}>
            <MessageScroller className="min-h-0 flex-1">
              <MessageScrollerViewport>
                <MessageScrollerContent aria-label="Conversa com o assistente" className="mx-auto w-full max-w-[900px] space-y-7 px-4 py-8 sm:px-6">
                  <ConversationView
                    turns={turns}
                    pending={pending}
                    failure={failure}
                    onRetry={handleRetry}
                    onSuggestion={handleSubmit}
                    animateLastAssistant={animateNext}
                  />
                </MessageScrollerContent>
              </MessageScrollerViewport>
              <MessageScrollerButton />
            </MessageScroller>
          </MessageScrollerProvider>

          <div className="bg-gradient-to-t from-v0-background via-v0-background to-transparent px-4 pb-5 pt-2 sm:px-6">
            <div className="mx-auto w-full max-w-[900px]">
              <ChatComposer onSubmit={handleSubmit} pending={pending} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
