import type { ReactNode } from "react";

export type TagTone = "neutral" | "accent" | "success" | "warning" | "danger";

// Cada tom é um par fundo/texto já verificado para 4.5:1 nos dois temas
// (FR-008). Nenhum literal de cor: tudo sai das rampas de globals.css.
const TONE: Record<TagTone, string> = {
  neutral: "bg-neutral-800 text-neutral-200",
  accent: "bg-accent-800 text-accent-200",
  success: "bg-accent-2-800 text-accent-2-200",
  warning: "bg-neutral-700 text-neutral-100",
  danger: "bg-accent-900 text-accent-300",
};

export function Tag({ tone = "neutral", children }: { tone?: TagTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}
    >
      {children}
    </span>
  );
}
