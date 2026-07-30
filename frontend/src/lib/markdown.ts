import Link from "next/link";
import { createElement, type ReactNode } from "react";

import { NAV } from "@/lib/nav";

const ALLOWED_ROUTES = new Set(
  Object.values(NAV)
    .flat()
    .filter((item) => item.implemented)
    .map((item) => item.href),
);

const TOKEN_RE = /\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*/g;

// Parser mínimo para o campo `answer` do assistente (research.md R5): só
// negrito, itálico e link de navegação para uma rota já conhecida do app —
// nunca HTML, nunca URL livre (FR-045: conteúdo do modelo não é confiável).
// Rota fora da allow-list vira texto simples, não link clicável.
export function renderAssistantMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  TOKEN_RE.lastIndex = 0;
  while ((match = TOKEN_RE.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));

    const [, linkText, href, bold, italic] = match;
    if (linkText !== undefined && href !== undefined) {
      nodes.push(
        ALLOWED_ROUTES.has(href)
          ? createElement(
              Link,
              { key: key++, href, className: "text-link underline underline-offset-4" },
              linkText,
            )
          : linkText,
      );
    } else if (bold !== undefined) {
      nodes.push(createElement("strong", { key: key++ }, bold));
    } else if (italic !== undefined) {
      nodes.push(createElement("em", { key: key++ }, italic));
    }

    lastIndex = TOKEN_RE.lastIndex;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}
