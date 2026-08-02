"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

import { useTypewriter } from "./use-typewriter";
import { MarkdownMessage } from "./markdown-message";

interface TypewriterMessageProps {
  content: string;
  /** Skip the animation (e.g. for messages loaded from history). */
  animate?: boolean;
  /** Chamado sempre que o estado de digitação muda — usado pelo chamador pra
   *  esconder metadados complementares (fontes, contexto de ticket) até a
   *  resposta terminar de aparecer (specs/013). */
  onTypingChange?: (isTyping: boolean) => void;
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
export function TypewriterMessage({ content, animate = true, onTypingChange }: TypewriterMessageProps) {
  const { displayedText, isTyping } = useTypewriter(content, {
    chunkSize: 3,
    intervalMs: 18,
    // Movimento reduzido: entrega o texto inteiro de imediato (FR-012).
    enabled: animate,
  });

  useEffect(() => {
    onTypingChange?.(isTyping);
  }, [isTyping, onTypingChange]);

  // A reserva de altura final (abaixo) nasce em 0 e cresce até a altura real
  // num único ciclo de CSS — sem isso a altura final aparecia de uma vez já
  // no primeiro quadro, e pra uma resposta longa isso é um salto brusco só de
  // rolagem automática (o rolador segue o fundo do conteúdo): a "câmera"
  // pula de vez em vez de acompanhar. Com o crescimento suave, a rolagem
  // automática acompanha o mesmo ritmo, em vez de saltar.
  // `content` é fixo pro tempo de vida da instância (cada turno da
  // conversa monta uma instância nova, nunca recebe um `content` diferente
  // depois) — o estado nasce falso e só precisa virar verdadeiro uma vez.
  const [heightReady, setHeightReady] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setHeightReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  if (!animate || !isTyping) {
    return <MarkdownMessage content={content} />;
  }

  return (
    <div className="relative">
      {/* Só esta cópia entra no fluxo: ela sozinha define a altura. Nunca
          visível, nunca lida por leitor de tela. `grid-template-rows` anima
          de 0fr a 1fr (truque de altura "auto" animável em CSS puro) — a
          altura final ainda é conhecida desde o primeiro quadro, só passa a
          crescer suavemente até lá em vez de aparecer de um salto só. */}
      <div
        aria-hidden="true"
        className={cn(
          "invisible grid transition-[grid-template-rows] duration-500 ease-out",
          heightReady ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="min-h-0 overflow-hidden">
          <MarkdownMessage content={content} />
        </div>
      </div>
      {/* Fora do fluxo de propósito: assim nem o texto revelado nem o cursor
          piscante conseguem alterar a altura do bloco em quadro nenhum. */}
      <div className="absolute inset-0">
        <MarkdownMessage content={displayedText} className="v0-typewriter" />
      </div>
    </div>
  );
}
