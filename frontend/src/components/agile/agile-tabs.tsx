"use client";

// Backlog/Scrum/Kanban deixaram de ser itens da barra lateral (specs/005 —
// competiam com "Painel" pelo mesmo prefixo de rota e destacavam os dois
// ao mesmo tempo). Viram abas aqui dentro, junto da tela de Dashboard.
import Link from "next/link";
import { usePathname } from "next/navigation";

import { mostSpecificMatch } from "@/lib/nav";

const TABS = [
  { label: "Painel", href: "/agile" },
  { label: "Backlog", href: "/agile/backlog" },
  { label: "Quadro Scrum", href: "/agile/scrum" },
  { label: "Quadro Kanban", href: "/agile/kanban" },
] as const;

export function AgileTabs() {
  const pathname = usePathname();
  const current = mostSpecificMatch(TABS, pathname);

  return (
    <nav aria-label="Seções do Agile" className="shrink-0 flex gap-1 overflow-x-auto border-b border-divider px-4 md:px-6">
      {TABS.map((tab) => {
        const active = tab.href === current?.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
              active
                ? "border-primary text-text"
                : "border-transparent text-muted-foreground hover:text-text"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
