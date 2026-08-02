// Prioridade vem da origem (Freshservice) em inglês. Fonte única de
// tradução — evita o bug de traduzir só no filtro e deixar badge/detalhe
// crus (specs/011).
export const PRIORITY_LABELS: Record<string, string> = {
  urgent: "Urgente",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export const PRIORITY_OPTIONS = [
  ["", "Todas as prioridades"],
  ["urgent", "Urgente"],
  ["high", "Alta"],
  ["medium", "Média"],
  ["low", "Baixa"],
] as const;
