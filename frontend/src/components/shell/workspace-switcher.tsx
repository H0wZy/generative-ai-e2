import Link from "next/link";

import type { Workspace } from "@/lib/types";

const OPTIONS: { id: Workspace; label: string; href: string }[] = [
  { id: "itsm", label: "ITSM", href: "/itsm" },
  { id: "agile", label: "Ágil", href: "/agile" },
];

// Sem estado e sem cliente: dois <Link> do App Router. É o que faz a troca de
// workspace acontecer por navegação, não por recarga (SC-003).
export function WorkspaceSwitcher({ current }: { current: Workspace }) {
  return (
    <div
      className="grid grid-cols-2 gap-1 rounded-xl bg-elevated/60 p-1"
      role="group"
      aria-label="Workspace"
    >
      {OPTIONS.map((option) => {
        const active = option.id === current;
        return (
          <Link
            key={option.id}
            href={option.href}
            aria-current={active ? "true" : undefined}
            className={`rounded-lg px-3 py-1.5 text-center text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${
              active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-text"
            }`}
          >
            {option.label}
          </Link>
        );
      })}
    </div>
  );
}
