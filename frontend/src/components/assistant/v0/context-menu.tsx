// ContextMenu no estilo shadcn (registry: context-menu), namespace `v0/` como
// os demais primitivos da tela /assistant. CLI (`npx shadcn@latest add
// context-menu`) não roda sem TTY interativo neste ambiente (mesma limitação
// já documentada em v0/breadcrumb.tsx) — componente construído sobre o
// primitivo real `@base-ui/react/context-menu` (a mesma lib das demais peças
// desta tela), só a casca visual é "manual".
//
// Estilo alinhado com o registry oficial base-nova (jul/2026):
//   https://ui.shadcn.com/r/styles/base-nova/context-menu.json
import type { ComponentProps } from "react";
import { ContextMenu as ContextMenuPrimitive } from "@base-ui/react/context-menu";

import { cn } from "@/lib/utils";

const ContextMenu = ContextMenuPrimitive.Root;
const ContextMenuTrigger = ContextMenuPrimitive.Trigger;

function ContextMenuContent({
  className,
  sideOffset = 4,
  container,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Popup> & {
  sideOffset?: number;
  container?: ComponentProps<typeof ContextMenuPrimitive.Portal>["container"];
}) {
  return (
    <ContextMenuPrimitive.Portal container={container}>
      {/* `isolate z-50` no Positioner garante que o menu fique ACIMA da sidebar
          (z-40) mesmo quando o portal monta dentro de `.v0-assistant`. */}
      <ContextMenuPrimitive.Positioner
        sideOffset={sideOffset}
        className="isolate z-50 outline-none"
      >
        <ContextMenuPrimitive.Popup
          data-slot="context-menu-content"
          className={cn(
            // Surface escura em contraste com a sidebar, borda sutil de 1px e sombra elegante
            "z-50 max-h-[var(--available-height)] min-w-40 overflow-x-hidden overflow-y-auto rounded-lg border border-[#2f2f32] bg-v0-popover p-1 text-sm text-v0-popover-foreground shadow-2xl outline-none",
            // Animações de entrada/saída (mesmos data-attrs do base-ui)
            "origin-[var(--transform-origin)] transition-[transform,opacity] duration-100",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0",
            className,
          )}
          {...props}
        />
      </ContextMenuPrimitive.Positioner>
    </ContextMenuPrimitive.Portal>
  );
}

function ContextMenuItem({
  className,
  variant = "default",
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Item> & { variant?: "default" | "destructive" }) {
  return (
    <ContextMenuPrimitive.Item
      data-slot="context-menu-item"
      className={cn(
        "relative flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium text-v0-popover-foreground outline-none select-none transition-colors",
        "data-[highlighted]:bg-v0-accent data-[highlighted]:text-v0-accent-foreground",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
        variant === "destructive" &&
          "text-v0-destructive data-[highlighted]:bg-v0-destructive/15 data-[highlighted]:text-v0-destructive",
        className,
      )}
      {...props}
    />
  );
}

function ContextMenuSeparator({ className, ...props }: ComponentProps<typeof ContextMenuPrimitive.Separator>) {
  return (
    <ContextMenuPrimitive.Separator
      data-slot="context-menu-separator"
      className={cn("-mx-1 my-1 h-px bg-v0-border", className)}
      {...props}
    />
  );
}

export { ContextMenu, ContextMenuTrigger, ContextMenuContent, ContextMenuItem, ContextMenuSeparator };
