// Seções fechadas de FR-003. `implemented: false` roteia para
// /em-construcao/[secao] (FR-004) em vez de link inerte.

import { useEffect, useSyncExternalStore } from "react";
import {
  Blocks,
  BookOpen,
  Boxes,
  Home,
  KanbanSquare,
  LayoutDashboard,
  ListTodo,
  Settings,
  Sparkles,
  Workflow,
} from "lucide-react";

import type { Workspace } from "./types";

export type NavItem = {
  label: string;
  href: string;
  implemented: boolean;
};

// Ícone por rótulo de item de menu — mesmo mapeamento usado pela navegação do
// Assistente (conversation-sidebar.tsx), centralizado aqui para os dois
// consumidores (Sidebar do shell e ConversationSidebar) não divergirem.
export const NAV_ICONS: Record<string, typeof Home> = {
  Home,
  Dashboard: LayoutDashboard,
  Assets: Boxes,
  "Base de Conhecimento": BookOpen,
  Automações: Workflow,
  "Assistente de IA": Sparkles,
  Administração: Settings,
  Backlog: ListTodo,
  "Quadro Scrum": KanbanSquare,
  "Quadro Kanban": Blocks,
};

export const NAV: Record<Workspace, NavItem[]> = {
  itsm: [
    { label: "Home", href: "/", implemented: true },
    { label: "Dashboard", href: "/itsm", implemented: true },
    { label: "Assets", href: "/em-construcao/assets", implemented: false },
    { label: "Base de Conhecimento", href: "/em-construcao/base-de-conhecimento", implemented: false },
    { label: "Automações", href: "/em-construcao/automacoes", implemented: false },
    { label: "Assistente de IA", href: "/ai/chat", implemented: true },
    { label: "Administração", href: "/em-construcao/administracao", implemented: false },
  ],
  agile: [
    { label: "Home", href: "/", implemented: true },
    // Backlog/Scrum/Kanban não são itens de menu próprios — são abas dentro
    // da tela de Dashboard (AgileTabs, app/(shell)/agile/layout.tsx). Eram
    // 3 rotas irmãs sob /agile/*, o que fazia o item "Dashboard" (href
    // "/agile") ficar destacado ao mesmo tempo que qualquer uma delas (o
    // prefixo "/agile/" bate nos dois).
    { label: "Dashboard", href: "/agile", implemented: true },
    { label: "Assistente de IA", href: "/ai/chat", implemented: true },
    { label: "Administração", href: "/em-construcao/administracao", implemented: false },
  ],
};

/** Item de `items` cujo `href` melhor corresponde a `pathname` — o mais
 * específico (maior) entre os que batem, não o primeiro. Sem isso, um item
 * cujo `href` é prefixo de outro (ex.: "/agile" e "/agile/backlog") acende os
 * dois ao mesmo tempo. */
export function mostSpecificMatch<T extends { href: string }>(
  items: readonly T[],
  pathname: string,
): T | undefined {
  return items
    .filter((item) => pathname === item.href || (item.href !== "/" && pathname.startsWith(`${item.href}/`)))
    .sort((a, b) => b.href.length - a.href.length)[0];
}

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

const WORKSPACE_STORAGE_KEY = "active-workspace";

const workspaceListeners = new Set<() => void>();

function getStoredWorkspaceSnapshot(): Workspace {
  return window.localStorage.getItem(WORKSPACE_STORAGE_KEY) === "agile" ? "agile" : "itsm";
}

// SSR nunca vê localStorage — o servidor sempre devolve "itsm". Fixar isso
// como snapshot de servidor garante que a primeira renderização no cliente
// bate byte a byte com o HTML do servidor (React usa este snapshot até a
// hidratação terminar), o que elimina a divergência na raiz em vez de
// mascará-la: antes, `useState(() => ... ?? readStoredWorkspace())` lia
// localStorage já na primeira renderização do cliente, que podia divergir do
// "itsm" fixo do servidor e disparar `Hydration failed`.
function getServerWorkspaceSnapshot(): Workspace {
  return "itsm";
}

function subscribeToWorkspace(listener: () => void): () => void {
  workspaceListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    workspaceListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function writeStoredWorkspace(workspace: Workspace): void {
  window.localStorage.setItem(WORKSPACE_STORAGE_KEY, workspace);
  workspaceListeners.forEach((listener) => listener());
}

/**
 * Workspace ativo da UI: preserva o último valor inequívoco em vez de
 * assumir ITSM em rota compartilhada (FR-056, corrige o bug de troca
 * sozinha). Persistido em localStorage porque `/ai/chat` é uma rota fora
 * do grupo `(shell)` — navegar até ela desmonta a sidebar do shell e monta
 * uma instância nova (specs/005), que sem isso perderia de vista qual
 * workspace estava ativo e caía sempre em ITSM. Compartilhado pela sidebar
 * única (app-sidebar.tsx) e pela Topbar, pra nunca divergirem.
 */
export function useActiveWorkspace(pathname: string): Workspace {
  const stored = useSyncExternalStore(
    subscribeToWorkspace,
    getStoredWorkspaceSnapshot,
    getServerWorkspaceSnapshot,
  );
  const resolved = workspaceFor(pathname);

  useEffect(() => {
    if (resolved) writeStoredWorkspace(resolved);
  }, [resolved]);

  return resolved ?? stored;
}

/** Rótulo da seção ativa, para a topbar. Item mais específico vence. */
export function sectionLabel(pathname: string): string {
  // Fora do NAV de propósito (A-004): "Arquivadas" é um destino próprio, não
  // uma seção sempre visível na barra lateral.
  if (pathname.startsWith("/ai/arquivadas")) return "Conversas arquivadas";
  // Rota compartilhada existe com o mesmo rótulo nos dois arrays de NAV
  // (Home, Assistente de IA, Administração) — "itsm" é só um array de busca,
  // não uma afirmação sobre o workspace ativo.
  const match = mostSpecificMatch(NAV[workspaceFor(pathname) ?? "itsm"], pathname);
  return match?.label ?? "Home";
}
