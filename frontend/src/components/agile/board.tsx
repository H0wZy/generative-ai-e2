"use client";

import { useRef, useState } from "react";

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
  // Coluna sob o cursor durante um arrasto ativo — indicador de "soltar
  // aqui", distinto do aviso de WIP estourado (specs/009 US3).
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
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
        {columns.map((column) => {
          const isDropTarget = dragOverColumn === column.name && dragging !== null;
          return (
            <section
              key={column.name}
              onDragOver={(event) => event.preventDefault()}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragOverColumn(column.name);
              }}
              onDragLeave={(event) => {
                // dragenter/dragleave disparam pra cada filho também — só
                // limpa quando o cursor realmente saiu da seção (não entrou
                // num descendente dela), senão o indicador pisca.
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                  setDragOverColumn((current) => (current === column.name ? null : current));
                }
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (dragging) void move(dragging.key, dragging.from, column.name);
                setDragging(null);
                setDragOverColumn(null);
              }}
              className={`flex w-64 shrink-0 flex-col gap-2 min-h-0 overflow-y-auto rounded-lg border border-transparent bg-surface p-3 shadow-sm transition-colors ${
                column.over_wip ? "outline-2 outline-link" : ""
              } ${isDropTarget ? "border-dashed border-primary bg-elevated" : ""}`}
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
              {isDropTarget && (
                <p className="text-xs text-link">Soltar aqui para mover</p>
              )}

              {column.cards.map((card) => (
                <BoardCard
                  key={card.key}
                  card={card}
                  columnName={column.name}
                  columnNames={columns.map((c) => c.name)}
                  disabled={moving}
                  isDragging={dragging?.key === card.key}
                  onDragStart={() => setDragging({ key: card.key, from: column.name })}
                  onDragEnd={() => {
                    // Sempre roda, drop bem-sucedido ou não (mouse solto fora
                    // de qualquer coluna, Esc, saiu da janela) — sem isto o
                    // card fica preso em estado "fantasma" pra sempre se o
                    // drop não acontecer sobre uma coluna válida.
                    setDragging(null);
                    setDragOverColumn(null);
                  }}
                  onMove={(to) => void move(card.key, column.name, to)}
                />
              ))}

              {column.cards.length === 0 && (
                <p className="py-4 text-center text-xs text-muted-foreground">Coluna vazia</p>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}

function BoardCard({
  card,
  columnName,
  columnNames,
  disabled,
  isDragging,
  onDragStart,
  onDragEnd,
  onMove,
}: {
  card: WorkItem;
  columnName: string;
  columnNames: string[];
  disabled: boolean;
  isDragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onMove: (to: string) => void;
}) {
  const articleRef = useRef<HTMLElement>(null);

  // Sem isto, o navegador tira a "foto" de arrasto do próprio nó ao vivo —
  // que aqui contém um <Select> (trigger + conteúdo potencialmente
  // portalado). Em alguns navegadores essa captura implícita sai
  // corrompida/expandida, arrastando visualmente elementos que não são o
  // card (specs/009 research.md). Um clone estático off-screen, sem o
  // conteúdo interativo, garante que a imagem de arrasto é sempre só o
  // card em si.
  function handleDragStart(event: React.DragEvent<HTMLElement>) {
    const node = articleRef.current;
    if (node && event.dataTransfer) {
      const clone = node.cloneNode(true) as HTMLElement;
      clone.style.position = "fixed";
      clone.style.top = "-9999px";
      clone.style.left = "-9999px";
      clone.style.width = `${node.offsetWidth}px`;
      clone.style.pointerEvents = "none";
      document.body.appendChild(clone);
      event.dataTransfer.setDragImage(clone, node.offsetWidth / 2, 16);
      window.setTimeout(() => clone.remove(), 0);
    }
    onDragStart();
  }

  return (
    <article
      ref={articleRef}
      draggable={!disabled}
      onDragStart={handleDragStart}
      onDragEnd={onDragEnd}
      className={`flex flex-col gap-2 rounded-md border-l-[3px] bg-elevated p-2 transition-opacity ${workItemStatusRail(card)} ${
        isDragging ? "opacity-40" : ""
      }`}
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
          esticando a área rolável da página (specs/006 research.md R1).
          `draggable={false}` aqui: o card pai é `draggable`, e sem opt-out
          explícito um mousedown no trigger do Select pode ser capturado
          pelo navegador como início de arrasto do card ao redor em vez de
          abrir o dropdown (specs/009). */}
      <div draggable={false} className="flex items-center gap-1 text-xs text-muted-foreground">
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
