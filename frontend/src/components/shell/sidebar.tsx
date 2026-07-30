"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV, useActiveWorkspace } from "@/lib/nav";

import { WorkspaceSwitcher } from "./workspace-switcher";

// Divergência de contracts/ui-routes.md: a sidebar é cliente, não servidor.
// Um layout de servidor não recebe o pathname no App Router, e a alternativa
// (middleware gravando um header) seria mais peça para o mesmo resultado.
// Só o `usePathname` roda no cliente; o conteúdo é estático.
export function Sidebar() {
  const pathname = usePathname();
  const workspace = useActiveWorkspace(pathname);

  return (
    <nav
      aria-label="Navegação principal"
      // Abaixo de md a barra vira uma faixa horizontal rolável: a 360 px uma
      // coluna de 14rem comeria a tela (FR-009), e um drawer seria estado e
      // JavaScript para o mesmo alcance de links.
      className="flex shrink-0 flex-col gap-4 border-b border-divider bg-surface p-4 md:w-56 md:border-b-0 md:border-r"
    >
      <Link
        href="/"
        className="inline-flex min-h-9 items-center text-sm font-semibold text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        ITSM <span className="text-link">+</span> Agile
      </Link>

      <WorkspaceSwitcher current={workspace} />

      <ul className="flex gap-0.5 overflow-x-auto md:flex-col md:overflow-visible">
        {NAV[workspace].map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(`${item.href}/`));
          return (
            <li key={item.label} className="shrink-0 md:shrink">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-9 items-center justify-between gap-2 rounded-md px-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
                  active
                    ? "bg-accent-800 text-neutral-100"
                    : "text-muted hover:bg-elevated hover:text-text"
                }`}
              >
                {item.label}
                {!item.implemented && (
                  // No item ativo o fundo é escuro nos dois temas, então o
                  // selo herda a cor do item em vez de usar `text-muted` —
                  // que no tema claro daria 1,57:1 sobre o roxo.
                  <span
                    className={`text-[10px] uppercase tracking-wide ${
                      active ? "text-neutral-300" : "text-muted"
                    }`}
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
  );
}
