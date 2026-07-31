"use client";

import { useState, type RefObject } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Blocks,
  BookOpen,
  Boxes,
  Home,
  KanbanSquare,
  LayoutDashboard,
  ListTodo,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Settings,
  Sparkles,
  Star,
  Trash2,
  Workflow,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV } from "@/lib/nav";
import type { ConversationSummary, Workspace } from "@/lib/types";

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "./v0/context-menu";

const ICONS: Record<string, typeof Home> = {
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

interface ConversationSidebarProps {
  open: boolean;
  onClose: () => void;
  onNewConversation: () => void;
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onToggleFavorite: (id: string, next: boolean) => void;
  onDeleteConversation: (id: string) => void;
  // Menu de contexto é um portal — precisa montar dentro de `.v0-assistant`
  // pra herdar os tokens de cor `v0-*` (ver ai-assistant.tsx).
  portalContainerRef: RefObject<HTMLDivElement | null>;
}

export function ConversationSidebar({
  open,
  onClose,
  onNewConversation,
  conversations,
  activeConversationId,
  onSelectConversation,
  onRenameConversation,
  onToggleFavorite,
  onDeleteConversation,
  portalContainerRef,
}: ConversationSidebarProps) {
  const [workspace, setWorkspace] = useState<Workspace>("itsm");
  // Colapso é conceito só de desktop — no mobile a sidebar já é off-canvas
  // (translate-x). Estado local, não precisa persistir.
  const [collapsed, setCollapsed] = useState(false);
  // Renomear é inline (troca o botão por um input) — sem modal pra uma ação
  // tão pequena.
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const pathname = usePathname();

  function startRename(conversation: ConversationSummary) {
    setRenamingId(conversation.id);
    setRenameValue(conversation.title || "Nova conversa");
  }

  function commitRename() {
    const trimmed = renameValue.trim();
    if (renamingId && trimmed) onRenameConversation(renamingId, trimmed);
    setRenamingId(null);
  }

  function handleDelete(conversation: ConversationSummary) {
    const label = conversation.title || "Nova conversa";
    if (window.confirm(`Excluir "${label}"? Essa ação não pode ser desfeita.`)) {
      onDeleteConversation(conversation.id);
    }
  }

  const favorites = conversations.filter((conversation) => conversation.is_favorite);
  const recents = conversations.filter((conversation) => !conversation.is_favorite);

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Fechar menu"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col border-r border-v0-sidebar-border bg-v0-sidebar text-v0-sidebar-foreground transition-all duration-300 lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
          collapsed && "lg:w-[68px]",
        )}
      >
        <div
          className={cn(
            "flex items-center justify-between px-5 pt-5 pb-4",
            collapsed && "lg:flex-col lg:gap-2 lg:px-3",
          )}
        >
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-v0-primary text-v0-primary-foreground">
              <Sparkles className="size-4" />
            </div>
            <div className={cn("leading-tight", collapsed && "lg:hidden")}>
              <p className="text-sm font-semibold">ITSM+Agile</p>
              <p className="text-[11px] text-v0-muted-foreground">Assistente</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar menu"
            className="rounded-md p-1 text-v0-muted-foreground transition-colors hover:bg-v0-sidebar-accent hover:text-v0-sidebar-foreground lg:hidden"
          >
            <X className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            title={collapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
            aria-label={collapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
            className="hidden rounded-md p-1 text-v0-muted-foreground transition-colors hover:bg-v0-sidebar-accent hover:text-v0-sidebar-foreground lg:flex"
          >
            {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
          </button>
        </div>

        <div className={cn("px-4", collapsed && "lg:hidden")}>
          <div className="flex gap-1 rounded-xl bg-v0-accent/60 p-1">
            {(["itsm", "agile"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setWorkspace(option)}
                className={cn(
                  "flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                  workspace === option
                    ? "bg-v0-primary text-v0-primary-foreground"
                    : "text-v0-muted-foreground hover:text-v0-sidebar-foreground",
                )}
              >
                {option === "itsm" ? "ITSM" : "Agile"}
              </button>
            ))}
          </div>
        </div>

        <div className={cn("px-4 pt-4", collapsed && "lg:px-3")}>
          <button
            type="button"
            onClick={onNewConversation}
            title={collapsed ? "Nova conversa" : undefined}
            className={cn(
              "flex w-full items-center gap-2 rounded-xl border border-v0-sidebar-border bg-v0-accent/40 px-3 py-2.5 text-sm font-medium transition-colors hover:bg-v0-sidebar-accent",
              collapsed && "lg:justify-center lg:px-0",
            )}
          >
            <MessageSquarePlus className="size-4 shrink-0 text-v0-primary" />
            <span className={cn(collapsed && "lg:hidden")}>Nova conversa</span>
          </button>
        </div>

        <nav className={cn("px-3 pt-5", collapsed && "lg:px-2")}>
          <p className={cn("px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-v0-muted-foreground/70", collapsed && "lg:hidden")}>
            Navegação
          </p>
          <ul className="space-y-0.5">
            {NAV[workspace].map((item) => {
              const Icon = ICONS[item.label] ?? Home;
              const active = pathname === item.href;
              return (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
                      active
                        ? "bg-v0-sidebar-accent text-v0-sidebar-foreground"
                        : "text-v0-muted-foreground hover:bg-v0-sidebar-accent/60 hover:text-v0-sidebar-foreground",
                      collapsed && "lg:justify-center lg:px-0",
                    )}
                  >
                    <Icon className={cn("size-4 shrink-0", active ? "text-v0-primary" : "text-current")} />
                    <span className={cn(collapsed && "lg:hidden")}>{item.label}</span>
                    {!item.implemented && (
                      <span className={cn("ml-auto text-[10px] uppercase tracking-wide text-v0-muted-foreground", collapsed && "lg:hidden")}>
                        em breve
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className={cn("mt-5 flex min-h-0 flex-1 flex-col px-3", collapsed && "lg:hidden")}>
          {favorites.length > 0 && (
            <>
              <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-v0-muted-foreground/70">
                Favoritos
              </p>
              <ul className="space-y-0.5 pb-3">
                {favorites.map((conversation) => (
                  <ConversationRow
                    key={conversation.id}
                    conversation={conversation}
                    active={conversation.id === activeConversationId}
                    isEditing={renamingId === conversation.id}
                    editValue={renameValue}
                    onEditValueChange={setRenameValue}
                    onCommitEdit={commitRename}
                    onCancelEdit={() => setRenamingId(null)}
                    onSelect={() => onSelectConversation(conversation.id)}
                    onStartRename={() => startRename(conversation)}
                    onToggleFavorite={() => onToggleFavorite(conversation.id, false)}
                    onDelete={() => handleDelete(conversation)}
                    portalContainerRef={portalContainerRef}
                  />
                ))}
              </ul>
            </>
          )}

          <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-v0-muted-foreground/70">
            Recentes
          </p>
          <ul className="v0-scrollbar-slim min-h-0 flex-1 space-y-0.5 overflow-y-auto pb-4">
            {recents.length === 0 && (
              <li className="px-2.5 py-2 text-xs text-v0-muted-foreground/70">
                {favorites.length > 0 ? "Nenhuma conversa recente." : "Nenhuma conversa ainda."}
              </li>
            )}
            {recents.map((conversation) => (
              <ConversationRow
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === activeConversationId}
                isEditing={renamingId === conversation.id}
                editValue={renameValue}
                onEditValueChange={setRenameValue}
                onCommitEdit={commitRename}
                onCancelEdit={() => setRenamingId(null)}
                onSelect={() => onSelectConversation(conversation.id)}
                onStartRename={() => startRename(conversation)}
                onToggleFavorite={() => onToggleFavorite(conversation.id, true)}
                onDelete={() => handleDelete(conversation)}
                portalContainerRef={portalContainerRef}
              />
            ))}
          </ul>
        </div>
      </aside>
    </>
  );
}

interface ConversationRowProps {
  conversation: ConversationSummary;
  active: boolean;
  isEditing: boolean;
  editValue: string;
  onEditValueChange: (value: string) => void;
  onCommitEdit: () => void;
  onCancelEdit: () => void;
  onSelect: () => void;
  onStartRename: () => void;
  onToggleFavorite: () => void;
  onDelete: () => void;
  portalContainerRef: RefObject<HTMLDivElement | null>;
}

function ConversationRow({
  conversation,
  active,
  isEditing,
  editValue,
  onEditValueChange,
  onCommitEdit,
  onCancelEdit,
  onSelect,
  onStartRename,
  onToggleFavorite,
  onDelete,
  portalContainerRef,
}: ConversationRowProps) {
  if (isEditing) {
    return (
      <li>
        <input
          autoFocus
          value={editValue}
          onChange={(event) => onEditValueChange(event.target.value)}
          onBlur={onCommitEdit}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onCommitEdit();
            }
            if (event.key === "Escape") {
              event.preventDefault();
              onCancelEdit();
            }
          }}
          className="block w-full truncate rounded-lg border border-v0-ring bg-v0-accent/40 px-2.5 py-2 text-left text-sm text-v0-sidebar-foreground outline-none"
        />
      </li>
    );
  }

  return (
    <li>
      <ContextMenu>
        <ContextMenuTrigger className="block">
          <button
            type="button"
            onClick={onSelect}
            aria-current={active ? "true" : undefined}
            className={cn(
              "flex w-full items-center gap-1.5 truncate rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
              active
                ? "bg-v0-sidebar-accent text-v0-sidebar-foreground"
                : "text-v0-muted-foreground hover:bg-v0-sidebar-accent/60 hover:text-v0-sidebar-foreground",
            )}
          >
            {conversation.is_favorite && (
              <Star className="size-3 shrink-0 fill-current text-v0-primary" aria-hidden />
            )}
            <span className="truncate">{conversation.title || "Nova conversa"}</span>
          </button>
        </ContextMenuTrigger>
        <ContextMenuContent container={portalContainerRef}>
          <ContextMenuItem onClick={onStartRename}>
            <Pencil className="size-3.5" />
            Renomear
          </ContextMenuItem>
          <ContextMenuItem onClick={onToggleFavorite}>
            <Star className="size-3.5" />
            {conversation.is_favorite ? "Remover dos favoritos" : "Favoritar"}
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem variant="destructive" onClick={onDelete}>
            <Trash2 className="size-3.5" />
            Excluir
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
    </li>
  );
}
