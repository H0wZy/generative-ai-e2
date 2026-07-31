"use client";

import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { useEffect, useState } from "react";

const LOTTIE_SRC = "https://lottie.host/073d281f-67f5-487e-b339-124d42e4c0cf/ufDaz74KBg.lottie";
// Acima disso a espera deixa de parecer normal e passa a parecer travada
// (achado de QA exploratório em 2026-07-30) — o texto muda de pool pra deixar
// claro que ainda está em andamento.
const SLOW_THRESHOLD_MS = 6000;
const ROTATION_MS = 2800;

const WAITING_MESSAGES = [
  "Consultando a documentação…",
  "Vasculhando os trechos certos…",
  "Juntando as peças…",
  "Garimpando a resposta…",
];
const SLOW_MESSAGES = [
  "Ainda processando, isso pode levar alguns segundos…",
  "Quase lá, prometo…",
  "Isso tá dando um trabalho, mas seguimos firmes…",
];

export function LoadingIndicator() {
  const [slow, setSlow] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_THRESHOLD_MS);
    return () => clearTimeout(timer);
  }, []);

  // Rotação das mensagens de espera — mesmo padrão do placeholder do
  // composer (chat-composer.tsx), pra sensação de "ainda vivo" na espera.
  useEffect(() => {
    const interval = setInterval(() => setTick((prev) => prev + 1), ROTATION_MS);
    return () => clearInterval(interval);
  }, []);

  const pool = slow ? SLOW_MESSAGES : WAITING_MESSAGES;
  const message = pool[tick % pool.length];

  return (
    <div role="status" className="flex items-center gap-2.5 self-start">
      <span aria-hidden="true" className="flex shrink-0 items-center justify-center">
        <DotLottieReact src={LOTTIE_SRC} loop autoplay style={{ width: 50, height: 50 }} />
      </span>
      <span key={tick} className="animate-suggestion text-sm text-v0-muted-foreground">
        {message}
      </span>
    </div>
  );
}
