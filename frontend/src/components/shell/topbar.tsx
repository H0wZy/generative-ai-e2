"use client";

import { usePathname } from "next/navigation";
import { PanelLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { sectionLabel, useActiveWorkspace } from "@/lib/nav";

const WORKSPACE_LABEL = { itsm: "ITSM", agile: "Ágil" } as const;

// Cliente pelo mesmo motivo da sidebar: o título vem do pathname.
export function Topbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const pathname = usePathname();
  const workspace = useActiveWorkspace(pathname);

  return (
    <header className="flex items-center gap-3 border-b border-divider px-4 py-3 md:px-6">
      <Button
        variant="ghost"
        size="icon"
        onClick={onOpenSidebar}
        aria-label="Abrir menu"
        className="text-muted-foreground md:hidden"
      >
        <PanelLeft className="size-4" />
      </Button>
      <h1 className="text-sm text-muted-foreground">
        <span className="text-text font-medium">{sectionLabel(pathname)}</span>
        <span aria-hidden> · </span>
        {WORKSPACE_LABEL[workspace]}
      </h1>
    </header>
  );
}
