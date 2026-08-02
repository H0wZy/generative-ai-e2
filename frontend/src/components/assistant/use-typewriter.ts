"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

interface UseTypewriterOptions {
  /** Characters revealed per tick. */
  chunkSize?: number;
  /** Milliseconds between ticks. */
  intervalMs?: number;
  /** Quando false, entrega o texto completo sem animar. */
  enabled?: boolean;
}

/* Preferência de movimento reduzido (FR-012) lida como store externa, não como
   estado sincronizado por efeito: matchMedia É uma fonte externa, e
   `useSyncExternalStore` já resolve SSR (snapshot do servidor) e mudança de
   preferência em tempo real, sem setState dentro de efeito. */
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = window.matchMedia(REDUCED_MOTION_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function getReducedMotion(): boolean {
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

/** No servidor não há matchMedia — assume movimento normal. */
function getReducedMotionServer(): boolean {
  return false;
}

/**
 * Gradually reveals `fullText` character-by-character.
 * Returns `{ displayedText, isTyping }` — when `isTyping` is false the full
 * text has been rendered and the consumer can swap in the rich (Markdown)
 * version without a visual jump.
 */
export function useTypewriter(
  fullText: string,
  { chunkSize = 3, intervalMs = 18, enabled = true }: UseTypewriterOptions = {},
) {
  const [displayedLength, setDisplayedLength] = useState(0);
  const prevTextRef = useRef("");
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotion,
    getReducedMotionServer,
  );

  const animating = enabled && !reducedMotion;

  // Reset when fullText changes (new message).
  useEffect(() => {
    if (fullText !== prevTextRef.current) {
      prevTextRef.current = fullText;
      setDisplayedLength(0);
    }
  }, [fullText]);

  useEffect(() => {
    if (!animating) return;
    if (displayedLength >= fullText.length) return;

    const timer = setInterval(() => {
      setDisplayedLength((prev) => {
        const next = Math.min(prev + chunkSize, fullText.length);
        if (next >= fullText.length) clearInterval(timer);
        return next;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [animating, fullText, displayedLength, chunkSize, intervalMs]);

  if (!animating) {
    return { displayedText: fullText, isTyping: false };
  }

  return {
    displayedText: fullText.slice(0, displayedLength),
    isTyping: displayedLength < fullText.length,
  };
}
