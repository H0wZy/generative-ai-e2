"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { workItemStatusRail } from "@/lib/agile-status";
import type { BoardColumnView, WorkItem } from "@/lib/types";

type DragState = { key: string; from: string } | null;

async function requestTransition(
  issueKey: string,
  targetColumn: string,
): Promise<{ ok: true; statusName: string } | { ok: false; message: string }> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  let response: Response;
  try {
    response = await fetch(`${base}/api/v1/agile/issues/${issueKey}/transition`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ target_column: targetColumn }),
    });
  } catch {
    return { ok: false, message: "Não foi possível contatar a API." };
  }

  const body = await response.json().catch(() => null);
  if (response.status === 200 && body?.applied) {
    return { ok: true, statusName: body.new_status_name };
  }
  if (body?.reason === "already_there") {
    return { ok: false, message: "O item já está nessa coluna." };
  }
  if (body?.reason === "no_transition") {
    const options = (body.available_transitions ?? []).join(", ");
    return { ok: false, message: `Sem caminho para essa coluna. Alcançável: ${options || "—"}.` };
  }
  if (body?.reason === "forbidden") {
    return { ok: false, message: "A credencial do Jira não tem permissão para transicionar." };
  }
  return { ok: false, message: "O Jira recusou a transição." };
}

export function Board({ initialColumns }: { initialColumns: BoardColumnView[] }) {
  const [columns, setColumns] = useState(initialColumns);
  const [dragging, setDragging] = useState<DragState>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Serializa moves: com duas transições em voo, o revert da primeira (que
  // usa o `columns` capturado antes de começar) sobrescreveria o efeito
  // otimista da segunda. Trava input (drag e select) até a resposta voltar.
  const [moving, setMoving] = useState(false);

  async function move(issueKey: string, from: string, to: string) {
    if (from === to || moving) return;
    const snapshot = columns;
    const card = columns
      .find((column) => column.name === from)
      ?.cards.find((item) => item.key === issueKey);
    if (!card) return;

    setMoving(true);

    // Otimista: move já, reverte se o Jira não confirmar (FR-048).
    setColumns((current) =>
      current.map((column) => {
        if (column.name === from) {
          return { ...column, cards: column.cards.filter((item) => item.key !== issueKey) };
        }
        if (column.name === to) {
          return { ...column, cards: [...column.cards, { ...card, column: to }] };
        }
        return column;
      }),
    );
    setNotice(null);

    const result = await requestTransition(issueKey, to);
    if (!result.ok) {
      setColumns(snapshot);
      setNotice(result.message);
      setMoving(false);
      return;
    }
    setColumns((current) =>
      current.map((column) =>
        column.name === to
          ? {
              ...column,
              cards: column.cards.map((item) =>
                // Status relido do Jira, não o esperado.
                item.key === issueKey ? { ...item, status_name: result.statusName } : item,
              ),
            }
          : column,
      ),
    );
    setMoving(false);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      {notice && (
        <p role="alert" className="text-sm text-text">
          {notice}
        </p>
      )}

      <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto overflow-y-hidden pb-2">
        {columns.map((column) => (
          <section
            key={column.name}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              if (dragging) void move(dragging.key, dragging.from, column.name);
              setDragging(null);
            }}
            className={`flex w-64 shrink-0 flex-col gap-2 min-h-0 overflow-y-auto rounded-lg bg-surface p-3 shadow-sm ${
              column.over_wip ? "outline-2 outline-link" : ""
            }`}
          >
            <header className="flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-medium text-text">{column.name}</h3>
              <span className="text-xs tabular-nums text-muted-foreground">
                {column.cards.length}
                {column.wip_max !== null && ` / ${column.wip_max}`}
              </span>
            </header>
            {column.over_wip && (
              <p className="text-xs text-text">Limite de WIP estourado</p>
            )}

            {column.cards.map((card) => (
              <BoardCard
                key={card.key}
                card={card}
                columnName={column.name}
                columnNames={columns.map((c) => c.name)}
                disabled={moving}
                onDragStart={() => setDragging({ key: card.key, from: column.name })}
                onMove={(to) => void move(card.key, column.name, to)}
              />
            ))}

            {column.cards.length === 0 && (
              <p className="py-4 text-center text-xs text-muted-foreground">Coluna vazia</p>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function BoardCard({
  card,
  columnName,
  columnNames,
  disabled,
  onDragStart,
  onMove,
}: {
  card: WorkItem;
  columnName: string;
  columnNames: string[];
  disabled: boolean;
  onDragStart: () => void;
  onMove: (to: string) => void;
}) {
  return (
    <article
      draggable={!disabled}
      onDragStart={onDragStart}
      className={`flex flex-col gap-2 rounded-md border-l-[3px] bg-elevated p-2 ${workItemStatusRail(card)}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs text-muted-foreground">{card.key}</span>
        {card.points !== null && (
          <span className="text-xs tabular-nums text-muted-foreground">{card.points} pts</span>
        )}
      </div>
      <p className="text-sm text-text">{card.title}</p>

      <div className="flex flex-wrap items-center gap-1">
        {card.epic_name && <Badge variant="accent">{card.epic_name}</Badge>}
        {card.labels.map((label) => (
          <Badge key={label}>{label}</Badge>
        ))}
        {card.assignee && (
          <span
            className="ml-auto inline-flex size-6 items-center justify-center rounded-sm bg-accent-800 text-[10px] font-medium text-neutral-100"
            title={card.assignee.display_name}
          >
            {card.assignee.initials}
          </span>
        )}
      </div>

      {/* Arraste não pode ser o único caminho (FR-008): este select dispara a
          mesma requisição e é operável só com teclado.
          Sem `sr-only` aqui: o `aria-label` do próprio select já é o nome
          acessível efetivo (vence o texto do label), e o span era
          `position: absolute` sem ancestral posicionado — seu bloco contentor
          virava o documento, escapando de todo `overflow` da cadeia e
          esticando a área rolável da página (specs/006 research.md R1). */}
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Select
          value={columnName}
          onValueChange={(value) => onMove(String(value))}
          items={columnNames.map((name) => ({ label: name, value: name }))}
          disabled={disabled}
        >
          <SelectTrigger aria-label={`Mover ${card.key} para outra coluna`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {columnNames.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </article>
  );
}
