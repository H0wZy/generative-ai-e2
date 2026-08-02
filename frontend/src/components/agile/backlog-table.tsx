import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { workItemStatusRail } from "@/lib/agile-status";
import type { WorkItem } from "@/lib/types";

// Ordem vem ranqueada do Jira e não é reordenada aqui (FR-026).
export function BacklogTable({ items }: { items: WorkItem[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>#</TableHead>
          <TableHead>Item</TableHead>
          <TableHead>Título</TableHead>
          <TableHead>Épico</TableHead>
          <TableHead>Prioridade</TableHead>
          <TableHead>Pontos</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Responsável</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.key}>
            <TableCell
              className={`border-l-[3px] text-muted-foreground tabular-nums ${workItemStatusRail(item)}`}
            >
              {item.rank}
            </TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">{item.key}</TableCell>
            <TableCell className="text-text">{item.title}</TableCell>
            <TableCell className="text-muted-foreground">{item.epic_name ?? "—"}</TableCell>
            <TableCell>{item.priority ? <Badge>{item.priority}</Badge> : "—"}</TableCell>
            <TableCell className="tabular-nums text-muted-foreground">{item.points ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{item.status_name}</TableCell>
            <TableCell>
              {item.assignee ? (
                <span
                  className="inline-flex size-6 items-center justify-center rounded-sm bg-accent-800 text-[10px] font-medium text-neutral-100"
                  title={item.assignee.display_name}
                >
                  {item.assignee.initials}
                </span>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
