import { redirect } from "next/navigation";

// Rota antiga do Assistente, mantida só para os endereços já em circulação
// (favoritos do navegador, histórico, links colados). Redirecionamento de
// SERVIDOR de propósito: não deixa a rota antiga no histórico, então a barra
// de endereço termina no formato novo e o botão voltar não passa por aqui
// (specs/007 FR-016/FR-017).
export default async function AssistantRedirectPage({
  searchParams,
}: {
  searchParams: Promise<{ c?: string }>;
}) {
  const { c } = await searchParams;
  // `c` vem da URL e não é confiável: só vira segmento se tiver formato de
  // identificador. Qualquer outra coisa cai na conversa nova, não numa rota
  // montada com texto de terceiro (Constituição §II).
  const isId = typeof c === "string" && /^[0-9a-f-]{36}$/i.test(c);
  redirect(isId ? `/ai/chat/${c}` : "/ai/chat");
}
