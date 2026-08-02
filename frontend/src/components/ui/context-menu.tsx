// ContextMenu no estilo shadcn (registry: context-menu). CLI (`npx shadcn@latest
// add context-menu`) não roda sem TTY interativo neste ambiente (mesma
// limitação já documentada em assistant/v0/breadcrumb.tsx) — componente
// construído sobre o primitivo real `@base-ui/react/context-menu`.
//
// Movido de components/assistant/v0/ pra cá e restilizado com os tokens
// semânticos do produto (bg-elevated/text-text/border-divider/etc, já
// idênticos aos tokens v0-* — specs/005 research.md R2): usado tanto pela
// navegação do shell quanto pela do Assistente, então não pode depender do
// escopo `.v0-assistant` pra ter cor. Isso também elimina a necessidade de um
// `container` de portal dedicado — monta em `document.body` como qualquer
// outro menu de contexto do produto.
import type { ComponentProps } from "react";
import { ContextMenu as ContextMenuPrimitive } from "@base-ui/react/context-menu";

import { cn } from "@/lib/utils";

const ContextMenu = ContextMenuPrimitive.Root;
const ContextMenuTrigger = ContextMenuPrimitive.Trigger;

function ContextMenuContent({
  className,
  sideOffset = 4,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Popup> & { sideOffset?: number }) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Positioner sideOffset={sideOffset} className="isolate z-50 outline-none">
        <ContextMenuPrimitive.Popup
          data-slot="context-menu-content"
          className={cn(
            "z-50 max-h-[var(--available-height)] min-w-40 overflow-x-hidden overflow-y-auto rounded-lg border border-divider bg-elevated p-1 text-sm text-text shadow-2xl outline-none",
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
        "relative flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium text-text outline-none select-none transition-colors",
        "data-[highlighted]:bg-surface data-[highlighted]:text-text",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
        variant === "destructive" && "text-destructive data-[highlighted]:bg-destructive/15 data-[highlighted]:text-destructive",
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
      className={cn("-mx-1 my-1 h-px bg-divider", className)}
      {...props}
    />
  );
}

export { ContextMenu, ContextMenuTrigger, ContextMenuContent, ContextMenuItem, ContextMenuSeparator };
