import { AiAssistant } from "@/components/assistant/ai-assistant";

// Conversa nova: ainda não existe registro no servidor. Ela só é criada na
// primeira pergunta enviada (criação preguiçosa), e nesse momento o endereço
// passa a `/ai/chat/{id}` sem recarregar (specs/007 FR-005/FR-006).
//
// Sem `loading.tsx` neste segmento, de propósito. Medido: com um `loading.tsx`
// aqui, `/ai/chat` e `/ai/chat/[id]` param de hidratar — nenhum efeito roda,
// nenhuma requisição sai, e a tela fica congelada no HTML do servidor
// (`TypeError: Cannot read properties of null (reading 'parentNode')` em `$RS`,
// o injetor de stream do React). Reproduzido nos dois sentidos: com o arquivo
// quebra, sem ele funciona. E não faz falta — esta tela é cliente e já tem
// estado de carregamento próprio por conversa.
export default function NewChatPage() {
  return <AiAssistant conversationId={null} />;
}
