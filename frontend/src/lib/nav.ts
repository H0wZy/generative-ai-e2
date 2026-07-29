// Seções fechadas de FR-003. `implemented: false` roteia para
// /em-construcao/[secao] (FR-004) em vez de link inerte.

import type { Workspace } from "./types";

export type NavItem = {
  label: string;
  href: string;
  implemented: boolean;
};

export const NAV: Record<Workspace, NavItem[]> = {
  itsm: [
    { label: "Home", href: "/", implemented: true },
    { label: "Dashboard", href: "/itsm", implemented: true },
    { label: "Assets", href: "/em-construcao/assets", implemented: false },
    { label: "Base de Conhecimento", href: "/em-construcao/base-de-conhecimento", implemented: false },
    { label: "Reports", href: "/reports", implemented: true },
    { label: "Automações", href: "/em-construcao/automacoes", implemented: false },
    { label: "Assistente de IA", href: "/assistant", implemented: true },
    { label: "Administração", href: "/em-construcao/administracao", implemented: false },
  ],
  agile: [
    { label: "Home", href: "/", implemented: true },
    { label: "Dashboard", href: "/agile", implemented: true },
    { label: "Backlog", href: "/agile/backlog", implemented: true },
    { label: "Quadro Scrum", href: "/agile/scrum", implemented: true },
    { label: "Quadro Kanban", href: "/agile/kanban", implemented: true },
    { label: "Reports", href: "/reports", implemented: true },
    { label: "Assistente de IA", href: "/assistant", implemented: true },
    { label: "Administração", href: "/em-construcao/administracao", implemented: false },
  ],
};

/** Workspace derivado do primeiro segmento da URL. ITSM é o padrão. */
export function workspaceFor(pathname: string): Workspace {
  return pathname.startsWith("/agile") ? "agile" : "itsm";
}

/** Rótulo da seção ativa, para a topbar. Item mais específico vence. */
export function sectionLabel(pathname: string): string {
  const match = NAV[workspaceFor(pathname)]
    .filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return match?.label ?? "Home";
}
