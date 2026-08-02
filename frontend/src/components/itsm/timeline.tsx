import { EmptyState } from "@/components/ui/empty-state";
import type { TimelineEvent } from "@/lib/types";

// `detail` já chega filtrado por lista branca no servidor — aqui é só
// apresentação. Nada de renderizar HTML vindo do backend.
export function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return <EmptyState title="Sem eventos registrados" />;
  }

  return (
    <ol className="flex flex-col gap-3">
      {events.map((event, index) => (
        <li key={`${event.at}-${index}`} className="flex gap-3">
          <div className="flex flex-col items-center pt-1.5">
            <span className="size-2 shrink-0 rounded-sm bg-link" aria-hidden />
            {index < events.length - 1 && (
              <span className="mt-1 w-px flex-1 bg-divider" aria-hidden />
            )}
          </div>
          <div className="flex flex-col gap-0.5 pb-2">
            <p className="text-sm text-text">{event.summary}</p>
            <time dateTime={event.at} className="text-xs text-muted-foreground">
              {new Date(event.at).toLocaleString("pt-BR")}
            </time>
            {Object.keys(event.detail).length > 0 && (
              <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
                {Object.entries(event.detail).map(([key, value]) => (
                  <div key={key} className="flex gap-1">
                    <dt>{key}:</dt>
                    <dd className="text-text">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
