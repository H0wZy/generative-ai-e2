"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetch } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { AssistantAnswer, AssistantMessage, RetrievedSource, TicketRefSource } from "@/lib/types";

import { AssistantMessageView, UserMessage } from "./message";

type Turn =
  | { kind: "user"; text: string }
  | { kind: "assistant"; answer: AssistantAnswer };

interface ConversationMessage {
  role: "user" | "assistant";
  text: string;
  sources: RetrievedSource[] | null;
  ticket_context: TicketRefSource | null;
}

export function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  // Vazio durante SSR (getOrCreateSessionId só resolve no navegador); o
  // efeito abaixo o preenche antes de qualquer envio real acontecer.
  const sessionIdRef = useRef("");

  useEffect(() => {
    const sessionId = getOrCreateSessionId();
    sessionIdRef.current = sessionId;
    if (!sessionId) return;

    void apiFetch<{ messages: ConversationMessage[] }>("/api/v1/assistant/conversation", {
      headers: { "X-Session-Id": sessionId },
    }).then((result) => {
      if (!result.ok) return;
      setTurns(
        result.data.messages.map((message): Turn =>
          message.role === "user"
            ? { kind: "user", text: message.text }
            : {
                kind: "assistant",
                answer: {
                  status: "answered",
                  answer: message.text,
                  sources: message.sources ?? [],
                  truncated_history: false,
                  ticket_context: message.ticket_context ?? null,
                },
              },
        ),
      );
    });
  }, []);

  // Histórico de sessão: vive no componente, não em servidor nem localStorage.
  const history: AssistantMessage[] = turns.flatMap<AssistantMessage>((turn) =>
    turn.kind === "user"
      ? [{ role: "user", text: turn.text }]
      : turn.answer.answer
        ? [{ role: "assistant", text: turn.answer.answer }]
        : [],
  );

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || pending) return;

    setTurns((current) => [...current, { kind: "user", text: question }]);
    setDraft("");
    setPending(true);
    setFailure(null);

    const result = await apiFetch<AssistantAnswer>("/api/v1/assistant/ask", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "X-Session-Id": sessionIdRef.current,
      },
      body: JSON.stringify({ question, history: history.slice(-20) }),
    });

    setPending(false);
    if (!result.ok) {
      setFailure(result.error.message);
      return;
    }
    setTurns((current) => [...current, { kind: "assistant", answer: result.data }]);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        {turns.length === 0 && !pending && (
          <EmptyState
            title="Pergunte sobre a arquitetura do projeto"
            hint="As respostas saem da documentação indexada, com arquivo e linhas."
          />
        )}
        {turns.map((turn, index) =>
          turn.kind === "user" ? (
            <UserMessage key={index} text={turn.text} />
          ) : (
            <AssistantMessageView
              key={index}
              status={turn.answer.status}
              answer={turn.answer.answer}
              sources={turn.answer.sources}
              truncatedHistory={turn.answer.truncated_history}
              ticketContext={turn.answer.ticket_context}
            />
          ),
        )}
        {pending && (
          <p role="status" className="self-start text-sm text-muted">
            Consultando a documentação…
          </p>
        )}
        {failure && (
          <p role="alert" className="self-start text-sm text-text">
            {failure}
          </p>
        )}
      </div>

      <form onSubmit={send} className="flex items-end gap-2">
        <label className="flex-1">
          <span className="sr-only">Pergunta</span>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) void send(event);
            }}
            rows={2}
            maxLength={2000}
            placeholder="Como funciona a idempotência do worker?"
            className="w-full resize-y rounded-md border border-divider bg-surface px-3 py-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          />
        </label>
        <Button type="submit" variant="primary" disabled={pending || !draft.trim()}>
          Perguntar
        </Button>
      </form>
    </div>
  );
}
