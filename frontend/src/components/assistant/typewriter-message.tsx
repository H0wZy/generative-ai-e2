"use client";

import { useTypewriter } from "./use-typewriter";
import { MarkdownMessage } from "./markdown-message";

interface TypewriterMessageProps {
  content: string;
  /** Skip the animation (e.g. for messages loaded from history). */
  animate?: boolean;
}

/**
 * Revela a resposta progressivamente, já como Markdown de verdade.
 *
 * A altura final é reservada desde o primeiro quadro: duas cópias do mesmo
 * Markdown ocupam a MESMA célula de grid — a completa (invisível, fora da
 * árvore de acessibilidade) dita a altura, a revelada aparece por cima. A
 * célula assume a altura do maior filho, então o bloco nasce do tamanho final
 * e só o texto visível cresce dentro dele.
 *
 * Sem isso, o primeiro quadro renderizava Markdown de string vazia, o
 * contêiner de rolagem encolhia e o navegador prendia (`clamp`) o `scrollTop`
 * no novo máximo — a conversa saltava para o topo e voltava. Medido em
 * specs/006 research.md R2: `scrollTop` 3460 → 0 com `scrollHeight` 4129 →
 * 3821 no instante em que a revelação começava.
 */
export function TypewriterMessage({ content, animate = true }: TypewriterMessageProps) {
  const { displayedText, isTyping } = useTypewriter(content, {
    chunkSize: 3,
    intervalMs: 18,
    // Movimento reduzido: entrega o texto inteiro de imediato (FR-012).
    enabled: animate,
  });

  if (!animate || !isTyping) {
    return <MarkdownMessage content={content} />;
  }

  return (
    <div className="relative">
      {/* Só esta cópia entra no fluxo: ela sozinha define a altura, e a altura
          é a final desde o primeiro quadro. Nunca visível, nunca lida por
          leitor de tela. */}
      <div aria-hidden="true" className="invisible">
        <MarkdownMessage content={content} />
      </div>
      {/* Fora do fluxo de propósito: assim nem o texto revelado nem o cursor
          piscante conseguem alterar a altura do bloco em quadro nenhum. */}
      <div className="absolute inset-0">
        <MarkdownMessage content={displayedText} className="v0-typewriter" />
      </div>
    </div>
  );
}
