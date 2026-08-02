"use client";

// Estado do drawer mobile (aberto/fechado) precisa viver acima de Sidebar e
// Topbar — são irmãos no layout do shell, e é o Topbar (hambúrguer) quem abre
// o que a Sidebar (off-canvas) fecha. Mesmo papel que ai-assistant.tsx cumpre
// pra tela do Assistente, só que aqui em componente próprio porque o layout
// do App Router é servidor por padrão.
import { useState } from "react";

import { AppSidebar } from "./app-sidebar";
import { Topbar } from "./topbar";

export function ShellChrome({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-dvh flex-col overflow-hidden md:flex-row">
      <AppSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <Topbar onOpenSidebar={() => setSidebarOpen(true)} />
        {/* `relative` não é decoração: faz deste o bloco contentor de qualquer
            descendente `position: absolute` (rótulos `sr-only`, popovers).
            Sem ele o bloco contentor vira o documento, e o elemento escapa de
            todo `overflow` da cadeia, esticando a rolagem da página inteira
            (specs/006 research.md R1). */}
        <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
