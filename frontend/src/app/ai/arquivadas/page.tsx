"use client";

// Fora do grupo `(shell)`, junto de `/ai/chat`, e chamando `ShellChrome`
// diretamente: um mesmo segmento (`ai`) declarado dentro e fora de um grupo de
// rota faz o Next aplicar o layout errado e a hidratação de `/ai/chat/[id]`
// morrer. O grupo dá exatamente este componente — usar ele aqui custa uma
// linha e evita a ambiguidade.

import Link from "next/link";
import { Archive, ArchiveRestore, Trash2 } from "lucide-react";

import { ShellChrome } from "@/components/shell/shell-chrome";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { runUndoable } from "@/lib/undoable";
import { useConversations } from "@/lib/use-conversations";

export default function ArchivedConversationsPage() {
  const { conversations, archive, deleteConversation, removeLocally, restoreLocally } =
    useConversations("archived");

  function handleDelete(id: string, title: string) {
    // Mesma janela de desfazer das conversas ativas (FR-013). Desfazer devolve
    // a conversa a ESTA lista porque o objeto restaurado mantém `archived_at`.
    const target = conversations.find((conversation) => conversation.id === id);
    removeLocally(id);
    runUndoable({
      message: "Conversa excluída",
      description: title || "Nova conversa",
      onCommit: () => void deleteConversation(id),
      onUndo: () => target && restoreLocally(target),
    });
  }

  return (
    <ShellChrome>
      <div className="flex flex-col gap-4 p-4 md:p-6">
        <header>
          <h2 className="text-xl font-semibold text-text">Conversas arquivadas</h2>
          <p className="text-sm text-muted-foreground">
            Fora de “Favoritos” e “Recentes”, mas ainda acessíveis.
          </p>
        </header>

        <Card>
          {conversations.length === 0 ? (
            <EmptyState
              title="Nenhuma conversa arquivada"
              hint="Arquive uma conversa pelo menu de contexto na barra lateral."
            />
          ) : (
            <ul className="divide-y divide-divider">
              {conversations.map((conversation) => (
                <li
                  key={conversation.id}
                  className="flex flex-wrap items-center gap-3 px-4 py-3 first:pt-2 last:pb-2"
                >
                  <Archive className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <Link
                    href={`/ai/chat/${conversation.id}`}
                    className="min-w-0 flex-1 truncate text-sm text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                  >
                    {conversation.title || "Nova conversa"}
                  </Link>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void archive(conversation.id, false)}
                  >
                    <ArchiveRestore className="size-3.5" />
                    Desarquivar
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => handleDelete(conversation.id, conversation.title)}
                  >
                    <Trash2 className="size-3.5" />
                    Excluir
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </ShellChrome>
  );
}
