import type { RetrievedSource } from "@/lib/types";

// `content` é conteúdo indexado, não confiável: sai como texto simples dentro
// de <pre>, nunca como HTML nem Markdown com HTML habilitado (FR-045).
export function Sources({ sources }: { sources: RetrievedSource[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs uppercase tracking-wide text-muted">
        Fontes ({sources.length})
      </p>
      {sources.map((source) => (
        <details
          key={`${source.file_path}:${source.start_line}`}
          className="rounded-md border border-divider px-3 py-2"
        >
          <summary className="cursor-pointer text-xs text-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">
            <span className="font-mono text-text">{source.file_path}</span>
            {" · linhas "}
            {source.start_line}–{source.end_line}
            {source.heading_path && ` · ${source.heading_path}`}
          </summary>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs text-muted">
            {source.content}
          </pre>
        </details>
      ))}
    </div>
  );
}
