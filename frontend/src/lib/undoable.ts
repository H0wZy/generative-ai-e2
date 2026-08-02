"use client";

import { toast } from "sonner";

interface UndoableOptions {
  /** Texto principal do toast. */
  message: string;
  description?: string;
  /** Executa de verdade quando a janela de desfazer expira. */
  onCommit: () => void | Promise<void>;
  /** Reverte o efeito otimista na tela. */
  onUndo?: () => void;
  /** Janela para desfazer. */
  delayMs?: number;
}

/**
 * Ação com janela de desfazer.
 *
 * O backend não tem restore — `DELETE /conversations/{id}` apaga em definitivo
 * e cascateia as mensagens. Então "desfazer" aqui não desfaz nada: ele ADIA o
 * efeito real e cancela dentro da janela. A tela reage na hora (otimista), o
 * servidor só é chamado quando o tempo acaba.
 *
 * ponytail: se a aba fechar dentro da janela, o commit não acontece — a
 * conversa reaparece no próximo load. Aceitável porque o efeito é destrutivo
 * (falhar para o lado de NÃO apagar). Para tornar garantido seria preciso
 * soft-delete no backend, que é mudança de schema e está fora desta rodada.
 */
export function runUndoable({
  message,
  description,
  onCommit,
  onUndo,
  delayMs = 6000,
}: UndoableOptions): void {
  let undone = false;

  const timer = setTimeout(() => {
    if (!undone) void onCommit();
  }, delayMs);

  toast(message, {
    description,
    duration: delayMs,
    action: {
      label: "Desfazer",
      onClick: () => {
        undone = true;
        clearTimeout(timer);
        onUndo?.();
        toast.success("Ação desfeita");
      },
    },
  });
}
