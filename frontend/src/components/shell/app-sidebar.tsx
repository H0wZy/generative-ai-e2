"use client";

// Fonte única da barra lateral — usada tanto pelo shell (ITSM/Agile) quanto
// pela tela do Assistente de IA (via ai-assistant.tsx). Antes eram dois
// componentes que foram divergindo (ícones, padding do cabeçalho, cantos do
// alternador de workspace, Favoritos/Recentes só existindo num dos dois) —
// esta é a única versão de UI a partir de agora.
//
// Seleção/criação de conversa é injetável: quando embutida na tela do
// Assistente (que já tem a conversa aberta em memória), o pai passa
// `onSelectConversation`/`onNewConversation` pra tratar a troca junto com o
// estado local da conversa; em qualquer outra página, sem essas props, o
// padrão é navegar pra `/assistant` (com `?c=<id>` quando aplicável).
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Archive,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Sparkles,
  Star,
  Trash2,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV, mostSpecificMatch, sectionLabel, useActiveWorkspace } from "@/lib/nav";
import { useConversations } from "@/lib/use-conversations";
import { runUndoable } from "@/lib/undoable";
import type { ConversationSummary } from "@/lib/types";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { WorkspaceSwitcher } from "./workspace-switcher";

interface AppSidebarProps {
  open: boolean;
  onClose: () => void;
  activeConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
  onNewConversation?: () => void;
  // Injetáveis pela tela do Assistente, que já mantém sua própria cópia da
  // lista (precisa dela pra título da conversa ativa e pra atualizar a
  // ordenação depois de cada resposta) — sem isso, esta sidebar chamaria
  // useConversations() de novo e teria uma cópia própria, fora de sincronia
  // com o que a tela do Assistente acabou de mudar. Em qualquer outra
  // página, sem essas props, a sidebar busca e gerencia sua própria lista.
  conversations?: ConversationSummary[];
  onToggleFavorite?: (id: string, next: boolean) => void;
  onRenameConversation?: (id: string, title: string) => void;
  /** Commit da exclusão — só roda quando a janela de desfazer expira. */
  onDeleteConversation?: (id: string) => void;
  /** Efeito otimista: some da lista já, antes do commit. */
  onRemoveLocally?: (id: string) => void;
  /** Reverte o efeito otimista quando a pessoa desfaz. */
  onRestoreLocally?: (conversation: ConversationSummary) => void;
  /** Arquivar/desarquivar (specs/007). `isArchived=true` arquiva. */
  onArchiveConversation?: (id: string, isArchived: boolean) => void;
}

export function AppSidebar({
  open,
  onClose,
  activeConversationId = null,
  onSelectConversation,
  onNewConversation,
  conversations: conversationsProp,
  onToggleFavorite: onToggleFavoriteProp,
  onRenameConversation: onRenameProp,
  onDeleteConversation: onDeleteProp,
  onRemoveLocally: onRemoveLocallyProp,
  onRestoreLocally: onRestoreLocallyProp,
  onArchiveConversation: onArchiveProp,
}: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const workspace = useActiveWorkspace(pathname);
  const subtitle = sectionLabel(pathname);
  const currentNavItem = mostSpecificMatch(NAV[workspace], pathname);
  const ownConversationsApi = useConversations();
  const conversations = conversationsProp ?? ownConversationsApi.conversations;
  const toggleFavorite = onToggleFavoriteProp ?? ownConversationsApi.toggleFavorite;
  const rename = onRenameProp ?? ownConversationsApi.rename;
  const deleteConversation = onDeleteProp ?? ownConversationsApi.deleteConversation;
  const removeLocally = onRemoveLocallyProp ?? ownConversationsApi.removeLocally;
  const restoreLocally = onRestoreLocallyProp ?? ownConversationsApi.restoreLocally;
  const archive = onArchiveProp ?? ((id: string, isArchived: boolean) => void ownConversationsApi.archive(id, isArchived));

  // Colapso é conceito só de desktop — no mobile a sidebar já é off-canvas
  // (translate-x). Estado local, não precisa persistir.
  const [collapsed, setCollapsed] = useState(false);
  // Renomear é inline (troca o botão por um input) — sem modal pra uma ação
  // tão pequena.
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [pendingDelete, setPendingDelete] = useState<ConversationSummary | null>(null);

  function handleSelect(id: string) {
    if (onSelectConversation) onSelectConversation(id);
    else router.push(`/ai/chat/${id}`);
    onClose();
  }

  function handleNew() {
    if (onNewConversation) onNewConversation();
    else router.push("/ai/chat");
    onClose();
  }

  function handleArchive(conversation: ConversationSummary) {
    archive(conversation.id, true);
  }

  function startRename(conversation: ConversationSummary) {
    setRenamingId(conversation.id);
    setRenameValue(conversation.title || "Nova conversa");
  }

  function commitRename() {
    const trimmed = renameValue.trim();
    if (renamingId && trimmed) void rename(renamingId, trimmed);
    setRenamingId(null);
  }

  // O gatilho é um item de menu de contexto, não um botão — então o diálogo é
  // controlado por estado em vez de por `AlertDialogTrigger`. Antes era
  // `window.confirm`, que trava a thread e ignora o tema do produto.
  function handleDelete(conversation: ConversationSummary) {
    setPendingDelete(conversation);
  }

  function confirmDelete() {
    const target = pendingDelete;
    setPendingDelete(null);
    if (!target) return;

    // Some da lista na hora; o DELETE de verdade só sai quando a janela de
    // desfazer expira (o backend não tem restore — ver lib/undoable.ts).
    removeLocally(target.id);
    runUndoable({
      message: "Conversa excluída",
      description: target.title || "Nova conversa",
      onCommit: () => void deleteConversation(target.id),
      onUndo: () => restoreLocally(target),
    });
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
          // Cobre a tela inteira: alcançável por Tab prenderia o foco aqui
          // sem indicação visual nenhuma (T044) — não é um controle
          // navegável por teclado, é o clique-fora, o Escape/foco na
          // sidebar já fecham o menu.
          tabIndex={-1}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        aria-label="Navegação principal"
        className={cn(
          // font-sans (Inter) força a mesma fonte do resto do produto mesmo
          // aqui dentro — a tela do Assistente aplica Geist (font-v0-sans)
          // na árvore inteira via ai-assistant.tsx, e sem isso a sidebar
          // herdava Geist só quando renderizada ali, parecendo maior/
          // diferente das outras páginas (Geist e Inter têm métricas
          // diferentes no mesmo tamanho em px).
          "fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col border-r border-divider bg-surface font-sans text-text transition-all duration-300 md:static md:h-full md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
          collapsed && "md:w-[68px]",
        )}
      >
        <div
          className={cn(
            "flex items-center justify-between px-5 pt-5 pb-4",
            collapsed && "md:flex-col md:gap-2 md:px-3",
          )}
        >
          <Link
            href="/"
            className="flex items-center gap-2.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </span>
            <span className={cn("text-left leading-tight", collapsed && "md:hidden")}>
              <span className="block text-sm font-semibold text-text">
                ITSM<span className="text-link">+</span>Ágil
              </span>
              <span className="block text-[11px] text-muted-foreground">{subtitle}</span>
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Fechar menu"
            className="text-muted-foreground md:hidden"
          >
            <X className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setCollapsed((prev) => !prev)}
            title={collapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
            aria-label={collapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
            className="hidden text-muted-foreground md:flex"
          >
            {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
          </Button>
        </div>

        {!collapsed && (
          <div className="px-4">
            <WorkspaceSwitcher current={workspace} />
          </div>
        )}

        <div className={cn("px-4 pt-4", collapsed && "md:px-3")}>
          <Button
            variant="outline"
            onClick={handleNew}
            title={collapsed ? "Nova conversa" : undefined}
            className={cn(
              // Altura/raio próprios: este é um bloco de ação largo, não um
              // botão de barra — as medidas vêm do desenho da sidebar.
              "h-auto w-full justify-start gap-2 rounded-xl border-divider bg-elevated/40 px-3 py-2.5 font-medium text-text hover:bg-elevated",
              collapsed && "md:justify-center md:px-0",
            )}
          >
            <MessageSquarePlus className="size-4 shrink-0 text-primary" />
            <span className={cn(collapsed && "md:hidden")}>Nova conversa</span>
          </Button>
        </div>

        <div className={cn("px-4 pt-1.5", collapsed && "md:px-3")}>
          <Link
            href="/ai/arquivadas"
            onClick={onClose}
            title={collapsed ? "Arquivadas" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-elevated hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
              collapsed && "md:justify-center",
            )}
          >
            <Archive className="size-3.5 shrink-0" />
            <span className={cn(collapsed && "md:hidden")}>Arquivadas</span>
          </Link>
        </div>

        <nav className={cn("px-3 pt-5", collapsed && "md:px-2")}>
          <p
            className={cn(
              "px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70",
              collapsed && "md:hidden",
            )}
          >
            Navegação
          </p>
          <ul className="space-y-0.5">
            {NAV[workspace].map((item) => {
              const Icon = item.icon;
              // Item mais específico vence — evita que "Painel" (/agile)
              // acenda junto com uma rota irmã sob o mesmo prefixo.
              const active = item.href === currentNavItem?.href;
              return (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                      active
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-elevated hover:text-text",
                      collapsed && "md:justify-center md:px-0",
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                    <span className={cn(collapsed && "md:hidden")}>{item.label}</span>
                    {!item.implemented && (
                      // No item ativo o fundo é claro (bg-primary), então o
                      // selo usa a cor de texto do próprio item em vez de
                      // `text-muted-foreground` — que sobre bg-primary reprovaria
                      // contraste.
                      <span
                        className={cn(
                          "ml-auto text-[10px] uppercase tracking-wide",
                          active ? "text-primary-foreground/70" : "text-muted-foreground",
                          collapsed && "md:hidden",
                        )}
                      >
                        em breve
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {!collapsed && (
          <div className="mt-5 flex min-h-0 flex-1 flex-col px-3">
            {favorites.length > 0 && (
              <>
                <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
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
                      onSelect={() => handleSelect(conversation.id)}
                      onStartRename={() => startRename(conversation)}
                      onToggleFavorite={() => void toggleFavorite(conversation.id, false)}
                      onDelete={() => handleDelete(conversation)}
                      onArchive={() => handleArchive(conversation)}
                    />
                  ))}
                </ul>
              </>
            )}

            <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
              Recentes
            </p>
            <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto pb-4">
              {recents.length === 0 && (
                <li className="px-2.5 py-2 text-xs text-muted-foreground/70">
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
                  onSelect={() => handleSelect(conversation.id)}
                  onStartRename={() => startRename(conversation)}
                  onToggleFavorite={() => void toggleFavorite(conversation.id, true)}
                  onDelete={() => handleDelete(conversation)}
                  onArchive={() => handleArchive(conversation)}
                />
              ))}
            </ul>
          </div>
        )}
      </aside>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDelete(null);
        }}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogMedia className="text-destructive">
              <Trash2 />
            </AlertDialogMedia>
            <AlertDialogTitle>
              Excluir “{pendingDelete?.title || "Nova conversa"}”?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Essa ação é destrutiva se não for desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
  onArchive: () => void;
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
  onArchive,
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
          className="block w-full truncate rounded-lg border border-focus bg-elevated/40 px-2.5 py-2 text-left text-sm text-text outline-none"
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
              "flex w-full items-center gap-1.5 truncate rounded-lg px-2.5 py-2 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
              active ? "bg-elevated text-text" : "text-muted-foreground hover:bg-elevated/60 hover:text-text",
            )}
          >
            {conversation.is_favorite && (
              <Star className="size-3 shrink-0 fill-current text-primary" aria-hidden />
            )}
            <span className="truncate">{conversation.title || "Nova conversa"}</span>
          </button>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onClick={onStartRename}>
            <Pencil className="size-3.5" />
            Renomear
          </ContextMenuItem>
          <ContextMenuItem onClick={onToggleFavorite}>
            <Star className="size-3.5" />
            {conversation.is_favorite ? "Remover dos favoritos" : "Favoritar"}
          </ContextMenuItem>
          <ContextMenuItem onClick={onArchive}>
            <Archive className="size-3.5" />
            Arquivar
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
