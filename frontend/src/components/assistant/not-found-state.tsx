"use client";

import { MessageSquareOff } from "lucide-react";

import { Button } from "./v0/button";

// Tokens `v0-*` porque isto vive dentro da tela do Assistente (`.v0-assistant`),
// que tem paleta própria — os tokens do produto ficariam fora de tom aqui.
export function NotFoundState({ onNewConversation }: { onNewConversation: () => void }) {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-16 text-center">
      <div className="mb-6 flex size-14 items-center justify-center rounded-2xl bg-v0-muted text-v0-muted-foreground ring-1 ring-v0-border">
        <MessageSquareOff className="size-7" />
      </div>

      <h2 className="text-balance text-2xl font-semibold tracking-tight text-v0-foreground">
        Conversa não encontrada
      </h2>
      {/* Sem distinguir "não existe" de "é de outra sessão": o servidor
          responde igual nos dois casos de propósito (FR-014/SC-006), e a tela
          não pode ser mais específica que ele. */}
      <p className="mt-3 max-w-md text-pretty text-sm leading-relaxed text-v0-muted-foreground">
        Ela pode ter sido excluída, ou pertence a outra sessão deste navegador.
      </p>

      <Button
        type="button"
        variant="outline"
        onClick={onNewConversation}
        className="mt-8 h-auto rounded-xl bg-v0-card px-4 py-2.5 text-sm text-v0-card-foreground hover:border-v0-primary/40"
      >
        Iniciar nova conversa
      </Button>
    </div>
  );
}
