import type { WorkItem } from "./types";

// Status do Jira é texto livre (ver backend/app/domain/agile.py `status_name`),
// não um enum fechado como `WorkflowStatus` do ITSM — a heurística é por
// nome, não por id. Compartilhado por board.tsx e backlog-table.tsx (FR-055).
const DONE_PATTERN = /feito|conclu[ií]do|done|closed|resolvido/i;

/** Trilho de status (border-l-[3px]) para cards/linhas do Agile. */
export function workItemStatusRail(item: WorkItem): string {
  if (item.blocked_days !== null) return "border-l-status-critical";
  if (DONE_PATTERN.test(item.status_name)) return "border-l-status-ok";
  return "border-l-transparent";
}
