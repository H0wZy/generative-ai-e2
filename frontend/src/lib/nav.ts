// Seções fechadas de FR-003. `implemented: false` roteia para
// /em-construcao/[secao] (FR-004) em vez de link inerte.

import { useEffect, useState } from "react";

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
    { label: "Assistente de IA", href: "/assistant", implemented: true },
    { label: "Administração", href: "/em-construcao/administracao", implemented: false },
  ],
};

/**
 * Workspace derivado do primeiro segmento da URL, só para os casos
 * inequívocos. `null` para rota compartilhada (`/`, `/assistant`,
 * `/em-construcao/*`) — quem chama decide o que fazer com a ambiguidade
 * (contracts/ui-nav.md, FR-056). Função pura, sem estado.
 */
export function workspaceFor(pathname: string): Workspace | null {
  if (pathname.startsWith("/agile")) return "agile";
  if (pathname === "/itsm" || pathname.startsWith("/itsm/")) return "itsm";
  return null;
}

/**
 * Workspace ativo da UI: preserva o último valor inequívoco em vez de
 * assumir ITSM em rota compartilhada (FR-056, corrige o bug de troca
 * sozinha). Compartilhado por Sidebar e Topbar para os dois não divergirem.
 */
export function useActiveWorkspace(pathname: string): Workspace {
  const [workspace, setWorkspace] = useState<Workspace>(() => workspaceFor(pathname) ?? "itsm");

  useEffect(() => {
    const resolved = workspaceFor(pathname);
    if (resolved) setWorkspace(resolved);
  }, [pathname]);

  return workspace;
}

/** Rótulo da seção ativa, para a topbar. Item mais específico vence. */
export function sectionLabel(pathname: string): string {
  // Rota compartilhada existe com o mesmo rótulo nos dois arrays de NAV
  // (Home, Assistente de IA, Administração) — "itsm" é só um array de busca,
  // não uma afirmação sobre o workspace ativo.
  const match = NAV[workspaceFor(pathname) ?? "itsm"]
    .filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return match?.label ?? "Home";
}
