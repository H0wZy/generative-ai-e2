// Tipos de resposta da API. Fonte: specs/002-unified-itsm-agile-ui/data-model.md
// Nenhuma migration nesta feature — estes tipos espelham modelos Pydantic do
// backend, não tabelas.

// ---------------------------------------------------------------------------
// 1. ITSM — projeções sobre tabelas existentes
// ---------------------------------------------------------------------------

export type WorkflowStatus =
  | "pending"
  | "processing"
  | "completed"
  | "retry_scheduled"
  | "failed"
  | "needs_human_review";

export interface TicketDetail {
  source_ticket_id: string;
  subject: string;
  description: string;
  category: string | null;
  priority: string;
  requester: string | null;
  source_system: string;
}

export interface TimelineEvent {
  at: string;
  event_type: string;
  summary: string;
  detail: Record<string, unknown>;
}

export interface SlaState {
  available: boolean;
  minutes_left: number | null;
  tone: "ok" | "warning" | "critical" | "unknown";
}

export interface Metrics {
  received: number;
  pending: number;
  completed: number;
  retry_scheduled: number;
  failed: number;
  needs_human_review: number;
  duplicates_avoided: number | null;
}

export interface WorkflowListItem {
  workflow_execution_id: string;
  internal_correlation_id: string;
  status: WorkflowStatus;
  attempt_count: number;
  squad_id: string | null;
  routing_confidence: number | null;
  routing_rule_version: string | null;
  needs_human_review: boolean;
  last_error: string | null;
  jira_issue_key: string | null;
  link_origin: "deterministic" | "best_effort" | null;
  reprocess_eligible: boolean;
  ticket: {
    source_ticket_id: string;
    subject: string;
    category: string | null;
    priority: string;
  };
  updated_at: string;
}

export interface WorkflowListResponse {
  items: WorkflowListItem[];
  total: number;
}

export interface WorkflowDetail {
  workflow_execution_id: string;
  internal_correlation_id: string;
  status: WorkflowStatus;
  attempt_count: number;
  squad_id: string | null;
  routing_confidence: number | null;
  routing_rule_version: string | null;
  routing_reason: string | null;
  needs_human_review: boolean;
  last_error: string | null;
  next_attempt_at: string | null;
  jira_issue_key: string | null;
  jira_issue_url: string | null;
  link_origin: "deterministic" | "best_effort" | null;
  ticket: TicketDetail;
  timeline: TimelineEvent[];
  created_at: string;
  updated_at: string;
  reprocess_eligible: boolean;
}

// ---------------------------------------------------------------------------
// 2. Agile — projeções sobre o Jira, sem persistência
// ---------------------------------------------------------------------------

/** Causas nomeadas de indisponibilidade (contracts/api-agile.md). */
export type AvailabilityReason =
  | "not_configured"
  | "unauthorized"
  | "forbidden"
  | "unavailable"
  | "rate_limited"
  | "no_transition"
  | "already_there";

/** Envelope de indisponibilidade nomeada — toda leitura de Agile usa este formato. */
export type Availability<T> =
  | { available: true; reason: null; detail: null; data: T }
  | { available: false; reason: AvailabilityReason; detail: string | null; data: null };

export interface BoardColumn {
  name: string;
  status_ids: string[];
  wip_min: number | null;
  wip_max: number | null;
  over_wip: boolean;
}

/** Coluna já montada pelo backend, com os cards dentro. */
export interface BoardColumnView {
  name: string;
  wip_min: number | null;
  wip_max: number | null;
  over_wip: boolean;
  count: number;
  cards: WorkItem[];
}

export interface BoardView {
  constraint_type: string;
  columns: BoardColumnView[];
}

export interface BoardConfig {
  board_id: number;
  name: string;
  columns: BoardColumn[];
  constraint_type: "none" | "issueCount" | "issueCountExclSubs";
  estimation_field_id: string | null;
  done_status_ids: string[];
}

export interface Sprint {
  id: number;
  name: string;
  goal: string | null;
  state: "active" | "closed" | "future";
  start_date: string | null;
  end_date: string | null;
  days_left: number;
  committed_points: number;
  completed_points: number;
  scope_added_points: number;
}

export interface Person {
  display_name: string;
  initials: string;
  avatar_url: string | null;
}

export interface WorkItem {
  key: string;
  title: string;
  status_id: string;
  status_name: string;
  column: string | null;
  points: number | null;
  labels: string[];
  priority: string | null;
  assignee: Person | null;
  epic_key: string | null;
  epic_name: string | null;
  rank: number;
  blocked_days: number | null;
  blocked_reason: string | null;
}

export interface Epic {
  key: string;
  name: string;
  color: string;
  total_points: number;
  done_points: number;
  progress: number;
}

export interface BurndownSeries {
  days: string[];
  ideal: number[];
  actual: (number | null)[];
}

export interface VelocityPoint {
  sprint_name: string;
  committed: number;
  completed: number;
}

/** `data` de `GET /agile/sprint`. */
export interface SprintDashboard {
  board: { board_id: number; name: string };
  sprint: Sprint | null;
  burndown: BurndownSeries | null;
  velocity: VelocityPoint[];
  blocked: WorkItem[] | null;
}

export type TransitionReason =
  | "no_transition"
  | "already_there"
  | "forbidden"
  | "unavailable"
  | null;

export interface TransitionRequest {
  issue_key: string;
  target_column: string;
}

export interface TransitionResult {
  applied: boolean;
  new_status_name: string | null;
  reason: TransitionReason;
  available_transitions: string[];
}

// ---------------------------------------------------------------------------
// 3. Assistente de IA
// ---------------------------------------------------------------------------

export type AssistantRole = "user" | "assistant";

export interface AssistantMessage {
  role: AssistantRole;
  text: string;
}

export interface AssistantQuestion {
  question: string;
  history: AssistantMessage[];
}

export interface RetrievedSource {
  file_path: string;
  heading_path: string;
  start_line: number;
  end_line: number;
  distance: number;
  content: string;
}

export type AssistantStatus =
  | "answered"
  | "no_grounding"
  | "rate_limited"
  | "unavailable"
  | "timeout"
  | "disabled";

export interface AssistantAnswer {
  status: AssistantStatus;
  answer: string | null;
  sources: RetrievedSource[];
  truncated_history: boolean;
}

// ---------------------------------------------------------------------------
// 4. Entidades do shell — só no frontend
// ---------------------------------------------------------------------------

export type Workspace = "itsm" | "agile";

export interface Indicator {
  label: string;
  value: number | string | null;
  window: string;
  state: "ok" | "unavailable";
}
