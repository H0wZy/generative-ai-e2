"use client";

import { useState } from "react";
import { ChevronRight, FileText } from "lucide-react";

import { cn } from "@/lib/utils";
import type { RetrievedSource } from "@/lib/types";

// `content` é conteúdo indexado, não confiável: sempre texto simples dentro
// de <pre>, nunca HTML nem Markdown (FR-045) — mesma regra da mensagem antiga.
export function SourceAccordion({ sources }: { sources: RetrievedSource[] }) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-v0-border bg-v0-card/50">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left transition-colors hover:bg-v0-accent/50"
      >
        <ChevronRight
          className={cn(
            "size-4 text-v0-muted-foreground transition-transform duration-200",
            open && "rotate-90",
          )}
        />
        <span className="text-xs font-medium uppercase tracking-wide text-v0-muted-foreground">
          Fontes ({sources.length})
        </span>
      </button>

      {open && (
        <ul className="space-y-1.5 border-t border-v0-border px-1.5 py-1.5">
          {sources.map((source) => (
            <li
              key={`${source.file_path}:${source.start_line}`}
              className="rounded-lg px-2 py-2"
            >
              <div className="flex items-start gap-2.5">
                <FileText className="mt-0.5 size-3.5 shrink-0 text-v0-primary/70" />
                <span className="min-w-0">
                  <span className="block truncate font-mono text-xs text-v0-foreground">
                    {source.file_path} · linhas {source.start_line}–{source.end_line}
                  </span>
                  {source.heading_path && (
                    <span className="mt-0.5 block text-[11px] text-v0-muted-foreground">
                      {source.heading_path}
                    </span>
                  )}
                </span>
              </div>
              <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-md bg-v0-background px-2.5 py-2 text-[11px] leading-relaxed text-v0-muted-foreground">
                {source.content}
              </pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
