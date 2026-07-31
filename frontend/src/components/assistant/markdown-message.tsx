"use client";

import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { NAV } from "@/lib/nav";

const ALLOWED_ROUTES = new Set(
  Object.values(NAV)
    .flat()
    .filter((item) => item.implemented)
    .map((item) => item.href),
);

// react-markdown nunca processa HTML bruto por padrão (sem rehype-raw), então
// a única superfície de risco que sobra é link — por isso `a` valida contra a
// allow-list de rotas internas antes de virar link clicável, e nunca abre em
// nova aba para URL externa arbitrária (FR-045: conteúdo do modelo não é
// confiável, nunca URL livre). Desvio deliberado do export v0 original, que
// tratava todo link como confiável.
function AssistantLink({ href, children }: { href?: string; children?: ReactNode }) {
  if (href && ALLOWED_ROUTES.has(href)) {
    return (
      <Link href={href} className="font-medium text-v0-primary underline underline-offset-2">
        {children}
      </Link>
    );
  }
  return <>{children}</>;
}

function CodeBlock({ className, children }: ComponentProps<"code">) {
  const match = /language-(\w+)/.exec(className ?? "");
  const language = match?.[1];
  const isInline = !className;

  if (isInline) {
    return (
      <code className="rounded bg-v0-muted px-1.5 py-0.5 font-mono text-[0.85em] text-v0-foreground">
        {children}
      </code>
    );
  }

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-v0-border bg-v0-muted/40">
      {language && (
        <div className="flex items-center justify-between border-b border-v0-border px-4 py-2">
          <span className="font-mono text-xs uppercase tracking-wide text-v0-muted-foreground">
            {language === "mermaid" ? "diagrama (mermaid)" : language}
          </span>
        </div>
      )}
      <pre className="overflow-x-auto px-4 py-3">
        <code className="font-mono text-sm leading-relaxed text-v0-foreground">{children}</code>
      </pre>
    </div>
  );
}

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="text-pretty text-sm leading-relaxed text-v0-foreground">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-3 mt-5 text-lg font-semibold first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-5 text-base font-semibold first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-4 text-sm font-semibold first:mt-0">{children}</h3>
          ),
          p: ({ children }) => <p className="my-3 leading-relaxed first:mt-0 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="my-3 ml-5 list-disc space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="my-3 ml-5 list-decimal space-y-1.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: AssistantLink,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          hr: () => <hr className="my-5 border-v0-border" />,
          blockquote: ({ children }) => (
            <blockquote className="my-3 border-l-2 border-v0-border pl-4 text-v0-muted-foreground">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-v0-border">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-v0-muted/50">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-v0-border px-3 py-2 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-v0-border px-3 py-2 align-top">{children}</td>
          ),
          code: CodeBlock,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
