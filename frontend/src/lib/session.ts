// Identificador de sessão do assistente: gerado no navegador, nunca no
// servidor — não há login para amarrar a uma pessoa (FR-058/FR-059).
// Client-only: chame só de dentro de componentes "use client".

const STORAGE_KEY = "assistant-session-id";

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";

  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) return existing;

  const created = crypto.randomUUID();
  window.localStorage.setItem(STORAGE_KEY, created);
  return created;
}
