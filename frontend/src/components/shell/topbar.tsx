"use client";

import { usePathname } from "next/navigation";

import { sectionLabel, useActiveWorkspace } from "@/lib/nav";

import { ThemeToggle } from "./theme-toggle";

const WORKSPACE_LABEL = { itsm: "ITSM", agile: "Agile" } as const;

// Cliente pelo mesmo motivo da sidebar: o título vem do pathname.
export function Topbar() {
  const pathname = usePathname();
  const workspace = useActiveWorkspace(pathname);

  return (
    <header className="flex min-h-14 items-center justify-between gap-4 border-b border-divider px-4">
      <h1 className="text-sm text-muted">
        <span className="text-text font-medium">{sectionLabel(pathname)}</span>
        <span aria-hidden> · </span>
        {WORKSPACE_LABEL[workspace]}
      </h1>
      <ThemeToggle />
    </header>
  );
}
