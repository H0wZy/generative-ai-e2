"use client";

// Lista de conversas do Assistente + mutações (favoritar/renomear/excluir) —
// fonte única usada tanto pela navegação do shell (specs/005) quanto pela
// tela do Assistente, pra as duas nunca divergirem.

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { ConversationSummary } from "@/lib/types";

export function useConversations() {
  const sessionIdRef = useRef("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refresh = useCallback(async () => {
    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    const result = await apiFetch<{ conversations: ConversationSummary[] }>(
      "/api/v1/assistant/conversations",
      { headers: { "X-Session-Id": sessionId } },
    );
    if (result.ok) setConversations(result.data.conversations);
  }, []);

  useEffect(() => {
    sessionIdRef.current = getOrCreateSessionId();
    void refresh();
  }, [refresh]);

  const toggleFavorite = useCallback(
    async (id: string, next: boolean) => {
      const result = await apiFetch<ConversationSummary>(`/api/v1/assistant/conversations/${id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json", "X-Session-Id": sessionIdRef.current },
        body: JSON.stringify({ is_favorite: next }),
      });
      // Re-busca em vez de reordenar localmente — favoritar muda a posição
      // na lista (favoritos primeiro) e o servidor já sabe a ordem certa.
      if (result.ok) void refresh();
    },
    [refresh],
  );

  const rename = useCallback(
    async (id: string, title: string) => {
      const result = await apiFetch<ConversationSummary>(`/api/v1/assistant/conversations/${id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json", "X-Session-Id": sessionIdRef.current },
        body: JSON.stringify({ title }),
      });
      if (result.ok) {
        setConversations((current) =>
          current.map((conversation) => (conversation.id === id ? result.data : conversation)),
        );
      }
    },
    [],
  );

  const deleteConversation = useCallback(async (id: string) => {
    const result = await apiFetch<void>(`/api/v1/assistant/conversations/${id}`, {
      method: "DELETE",
      headers: { "X-Session-Id": sessionIdRef.current },
    });
    if (result.ok) {
      setConversations((current) => current.filter((conversation) => conversation.id !== id));
    }
    return result.ok;
  }, []);

  // Separado do acima porque a janela de desfazer precisa das duas metades
  // avulsas: some da tela agora, chama o servidor só quando o tempo expira.
  const removeLocally = useCallback((id: string) => {
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
  }, []);

  const restoreLocally = useCallback((conversation: ConversationSummary) => {
    setConversations((current) =>
      current.some((item) => item.id === conversation.id)
        ? current
        : // Reinsere na posição de origem: favoritos primeiro, depois por
          // `updated_at` — mesma ordem que o servidor devolve.
          [...current, conversation].sort((a, b) => {
            if (a.is_favorite !== b.is_favorite) return a.is_favorite ? -1 : 1;
            return b.updated_at.localeCompare(a.updated_at);
          }),
    );
  }, []);

  return {
    conversations,
    refresh,
    toggleFavorite,
    rename,
    deleteConversation,
    removeLocally,
    restoreLocally,
  };
}
