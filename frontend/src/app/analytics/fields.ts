// Shared by the server page and the client filter bar.
//
// It lives outside filter-bar.tsx on purpose: a plain value exported from a
// 'use client' module becomes a client reference, and the server component
// cannot iterate it ("ALL_FILTER_FIELDS is not iterable").

// Two groups, no field singled out: squad is not more important than fila.
export const FRESHSERVICE_FIELDS: { field: string; label: string }[] = [
  { field: 'squad', label: 'Squad' },
  { field: 'sistema', label: 'Sistema' },
  { field: 'tecnologia', label: 'Tecnologia' },
  { field: 'status_chamado', label: 'Status do chamado' },
  { field: 'impacto', label: 'Impacto' },
  { field: 'agente_tecnico', label: 'Agente/Técnico' },
  { field: 'empresa_resp', label: 'Empresa responsável' },
  { field: 'fila', label: 'Fila' },
  { field: 'legal_regulat', label: 'Legal/Regulatório' },
  { field: 'prazo', label: 'Prazo' },
  { field: 'impacto_servico_incidente', label: 'Impacto serviço/incidente' },
]

export const JIRA_FIELDS: { field: string; label: string }[] = [
  { field: 'issue_type', label: 'Tipo de issue' },
  { field: 'reporter', label: 'Relator' },
  { field: 'priority', label: 'Prioridade do card' },
  { field: 'status', label: 'Status do card' },
  { field: 'resolution', label: 'Resolução' },
  { field: 'assignee', label: 'Responsável' },
]

export const ALL_FILTER_FIELDS: string[] = [
  ...FRESHSERVICE_FIELDS,
  ...JIRA_FIELDS,
].map((f) => f.field)

export const PERIODICIDADES = [
  { value: 'dia', label: 'Dia' },
  { value: 'semana', label: 'Semana' },
  { value: 'quinzena', label: 'Quinzena' },
  { value: 'mes', label: 'Mês' },
  { value: 'trimestre', label: 'Trimestre' },
]

export type FilterOptions = Record<string, string[]>
