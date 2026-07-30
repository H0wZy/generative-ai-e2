import { Table, Td, Th, Tr } from "@/components/ui/table";
import { Tag } from "@/components/ui/tag";
import { workItemStatusRail } from "@/lib/agile-status";
import type { WorkItem } from "@/lib/types";

// Ordem vem ranqueada do Jira e não é reordenada aqui (FR-026).
export function BacklogTable({ items }: { items: WorkItem[] }) {
  return (
    <Table
      head={
        <>
          <Th>#</Th>
          <Th>Item</Th>
          <Th>Título</Th>
          <Th>Épico</Th>
          <Th>Prioridade</Th>
          <Th>Pontos</Th>
          <Th>Status</Th>
          <Th>Responsável</Th>
        </>
      }
    >
      {items.map((item) => (
        <Tr key={item.key}>
          <Td className={`border-l-[3px] text-muted tabular-nums ${workItemStatusRail(item)}`}>
            {item.rank}
          </Td>
          <Td className="font-mono text-xs text-muted">{item.key}</Td>
          <Td className="text-text">{item.title}</Td>
          <Td className="text-muted">{item.epic_name ?? "—"}</Td>
          <Td>{item.priority ? <Tag>{item.priority}</Tag> : "—"}</Td>
          <Td className="tabular-nums text-muted">{item.points ?? "—"}</Td>
          <Td className="text-muted">{item.status_name}</Td>
          <Td>
            {item.assignee ? (
              <span
                className="inline-flex size-6 items-center justify-center rounded-sm bg-accent-800 text-[10px] font-medium text-neutral-100"
                title={item.assignee.display_name}
              >
                {item.assignee.initials}
              </span>
            ) : (
              <span className="text-muted">—</span>
            )}
          </Td>
        </Tr>
      ))}
    </Table>
  );
}
