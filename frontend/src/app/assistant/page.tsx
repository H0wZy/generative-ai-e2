import { Chat } from "@/components/assistant/chat";

export default function AssistantPage() {
  return (
    <div className="flex flex-col gap-4 p-4 md:p-6">
      <header>
        <h2 className="text-xl font-semibold text-text">Assistente de IA</h2>
        <p className="text-sm text-muted">
          Respostas fundamentadas na documentação indexada do projeto
        </p>
      </header>
      <Chat />
    </div>
  );
}
