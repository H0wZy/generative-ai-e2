import { AiAssistant } from "@/components/assistant/ai-assistant";

// O identificador não é validado aqui: `AiAssistant` confere o formato antes
// de virar requisição e trata malformado, inexistente e "de outra sessão" com
// a mesma tela de ausência (FR-007/FR-014).
export default async function ChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AiAssistant conversationId={id} />;
}
