"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

/**
 * Produto é dark-only (specs/004), então não há `next-themes` aqui: o tema é
 * fixo e as cores saem dos tokens do projeto via `--normal-*`.
 */
function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      position="bottom-right"
      style={
        {
          "--normal-bg": "var(--color-elevated)",
          "--normal-text": "var(--color-text)",
          "--normal-border": "var(--color-divider)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "!rounded-xl !border-divider !bg-elevated !text-text !shadow-md",
          description: "!text-muted-foreground",
          actionButton: "!rounded-md !bg-primary !text-primary-foreground",
          cancelButton: "!rounded-md !bg-surface !text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
