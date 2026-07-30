"use client";

import { useState } from "react";

import { Tag } from "@/components/ui/tag";
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

  async function move(issueKey: string, from: string, to: string) {
    if (from === to) return;
    const snapshot = columns;
    const card = columns
      .find((column) => column.name === from)
      ?.cards.find((item) => item.key === issueKey);
    if (!card) return;

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
  }

  return (
    <div className="flex flex-col gap-3">
      {notice && (
        <p role="alert" className="text-sm text-text">
          {notice}
        </p>
      )}

      <div className="flex gap-3 overflow-x-auto pb-2">
        {columns.map((column) => (
          <section
            key={column.name}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              if (dragging) void move(dragging.key, dragging.from, column.name);
              setDragging(null);
            }}
            className={`flex w-64 shrink-0 flex-col gap-2 rounded-lg bg-surface p-3 shadow-sm ${
              column.over_wip ? "outline-2 outline-link" : ""
            }`}
          >
            <header className="flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-medium text-text">{column.name}</h3>
              <span className="text-xs tabular-nums text-muted">
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
                onDragStart={() => setDragging({ key: card.key, from: column.name })}
                onMove={(to) => void move(card.key, column.name, to)}
              />
            ))}

            {column.cards.length === 0 && (
              <p className="py-4 text-center text-xs text-muted">Coluna vazia</p>
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
  onDragStart,
  onMove,
}: {
  card: WorkItem;
  columnName: string;
  columnNames: string[];
  onDragStart: () => void;
  onMove: (to: string) => void;
}) {
  return (
    <article
      draggable
      onDragStart={onDragStart}
      className={`flex flex-col gap-2 rounded-md border-l-[3px] bg-elevated p-2 ${workItemStatusRail(card)}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs text-muted">{card.key}</span>
        {card.points !== null && (
          <span className="text-xs tabular-nums text-muted">{card.points} pts</span>
        )}
      </div>
      <p className="text-sm text-text">{card.title}</p>

      <div className="flex flex-wrap items-center gap-1">
        {card.epic_name && <Tag tone="accent">{card.epic_name}</Tag>}
        {card.labels.map((label) => (
          <Tag key={label}>{label}</Tag>
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
          mesma requisição e é operável só com teclado. */}
      <label className="flex items-center gap-1 text-xs text-muted">
        <span className="sr-only">Mover {card.key} para</span>
        <select
          value={columnName}
          onChange={(event) => onMove(event.target.value)}
          className="min-h-8 w-full rounded-sm border border-divider bg-surface px-1 text-xs text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          aria-label={`Mover ${card.key} para outra coluna`}
        >
          {columnNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
    </article>
  );
}
