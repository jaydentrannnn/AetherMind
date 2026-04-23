/**
 * lib/types.ts
 *
 * TypeScript interfaces mirroring backend Pydantic schemas.
 * SOURCE OF TRUTH: backend/app/schemas/models.py
 * Confirm all field names and optionality against FastAPI OpenAPI spec
 * at GET /openapi.json before wiring to real API calls.
 *
 * Versioned: v1 — April 2026
 */

// ─── Primitives ───────────────────────────────────────────────────────────────

/** ISO-8601 datetime string, e.g. "2026-04-21T14:32:11Z" */
export type ISODateString = string;

/** UUID string, e.g. "ae7f21b3-..." */
export type UUID = string;

/** Hostname pattern, e.g. "arxiv.org" */
export type HostnamePattern = string;


// ─── Sources & Citations ──────────────────────────────────────────────────────

/** Source type returned from tool calls */
export type SourceType = 'web' | 'arxiv' | 'pdf' | 'url' | 'code';

/**
 * A single retrieved source document.
 * Maps to: backend Source / SourceRecord model.
 */
export interface Source {
  id: string;               // source_id used for citation lookup
  title: string;
  url: string;
  domain: string;           // extracted hostname, e.g. "arxiv.org"
  snippet?: string;         // representative excerpt
  verified: boolean;        // set by guardrails citation verification pass
  type: SourceType;
}

/**
 * An inline citation within a report section claim.
 * Maps to: backend Citation model.
 */
export interface Citation {
  source_id: string;        // foreign key into Source.id
  snippet?: string;         // quote or excerpt that supports the claim
  verified: boolean;        // matches Source.verified after guardrails pass
}


// ─── Report Structure ─────────────────────────────────────────────────────────

export type BlockType = 'p' | 'table' | 'ul' | 'ol' | 'code';

export interface ParagraphBlock {
  type: 'p';
  text: string;
  citations?: string[];     // source_ids
}

export interface TableBlock {
  type: 'table';
  headers: string[];
  rows: string[][];
  citations?: string[];
}

export interface ListBlock {
  type: 'ul' | 'ol';
  items: string[];
  citations?: string[];
}

export interface CodeBlock {
  type: 'code';
  language?: string;
  text: string;
}

export type ContentBlock = ParagraphBlock | TableBlock | ListBlock | CodeBlock;

/**
 * A structured section within a report.
 * Maps to: backend ReportSection model.
 */
export interface ReportSection {
  id: string;
  title: string;
  content: ContentBlock[];
}

/**
 * Full report returned from GET /reports/{id}.
 * Maps to: backend Report model.
 */
export interface Report {
  id: UUID;
  job_id: UUID;
  title: string;
  summary?: string;
  markdown?: string;        // raw markdown fallback if sections not available
  sections: ReportSection[];
  sources: Source[];
  guardrails?: GuardrailReport;
  rubric?: Rubric;
  versions?: ReportVersionMeta[];
  depth: 'quick' | 'standard' | 'deep';
  created_at: ISODateString;
  // Observability — surface in Diagnostics footer if present
  trace_id?: string;
  request_id?: string;
}

/**
 * Lightweight version metadata from GET /reports/{id}/versions.
 */
export interface ReportVersionMeta {
  id: string;
  created_at: ISODateString;
  label: string;
  summary_diff?: string;    // human-readable description of what changed
}

/**
 * One row from GET /reports (research job index).
 */
export interface ResearchJobSummary {
  job_id: UUID;
  topic: string;
  status: string;
  created_at: ISODateString;
  latest_report_id: string | null;
}

/**
 * Full version object used when diffing.
 */
export interface ReportVersion extends ReportVersionMeta {
  markdown?: string;
  sections?: ReportSection[];
}


// ─── Guardrails ───────────────────────────────────────────────────────────────

export interface GuardrailViolation {
  claim: string;
  rationale: string;
  source_ids?: string[];
}

/**
 * Guardrail evaluation result.
 * Maps to: backend GuardrailReport model.
 */
export interface GuardrailReport {
  unverified_claims: GuardrailViolation[];
  policy_violations: GuardrailViolation[];
  closure_violations: GuardrailViolation[];
}


// ─── Critic / Rubric ─────────────────────────────────────────────────────────

export interface RubricDimension {
  score: number;
  max: number;
  label: string;
  rationale?: string;
}

/**
 * Critic rubric scorecard.
 * Maps to: backend Rubric / CriticResult model.
 */
export interface Rubric {
  depth?: RubricDimension;
  citations?: RubricDimension;
  clarity?: RubricDimension;
  coverage?: RubricDimension;
  accuracy?: RubricDimension;
  [key: string]: RubricDimension | undefined; // extensible
}


// ─── Memory ───────────────────────────────────────────────────────────────────

export type PreferenceSource = 'user' | 'inferred';

export interface Preference {
  key: string;
  value: string;
  source: PreferenceSource;
  updatedAt: ISODateString;
}

/**
 * Full memory preferences object.
 * Maps to: backend MemoryPreferences model.
 * GET /memory/preferences → MemoryPreferencesResponse
 * POST /memory/preferences → same shape
 */
export interface MemoryPreferences {
  preferences: Preference[];
  allow_domains: HostnamePattern[];
  deny_domains: HostnamePattern[];
}

/**
 * A single recalled memory item (from Chroma semantic search).
 * Maps to: backend RecalledMemory model.
 */
export interface RecalledMemory {
  id: UUID;
  title: string;
  snippet: string;
  score: number;            // cosine similarity [0, 1]
  date: ISODateString;
  report_id?: UUID;
}


// ─── API Request / Response shapes ───────────────────────────────────────────

/** POST /research */
export interface ResearchOptions {
  depth?: 'quick' | 'standard' | 'deep';
  tools?: {
    web?: boolean;
    arxiv?: boolean;
    pdf?: boolean;
    url?: boolean;
    code?: boolean;
  };
  preferred_domains?: HostnamePattern[];
}

export interface CreateResearchRequest {
  topic: string;
  options?: ResearchOptions;
}

export interface CreateResearchResponse {
  job_id: UUID;
}

/** POST /feedback */
export interface FeedbackRequest {
  report_id: UUID;
  accepted: boolean;
  user_comment?: string;
}

export interface FeedbackResponse {
  id: UUID;
  created_at: ISODateString;
}

/** GET /memory/search */
export interface MemorySearchResponse {
  results: RecalledMemory[];
  query: string;
}


// ─── SSE Event Types ─────────────────────────────────────────────────────────
// Confirm event names against LangGraph pipeline event schema in backend.

export type SSEEventType =
  | 'planner'
  | 'researcher'
  | 'tool'
  | 'synthesizer'
  | 'guardrails'
  | 'critic'
  | 'revision'
  | 'memory'
  | 'done'
  | 'error';

export interface SSEEnvelope {
  type: SSEEventType;
  msg: string;
  ts?: number;              // ms since job start
  detail?: string;          // expandable JSON or text
  latency?: string;         // tool call latency, e.g. "312ms"
  // Observability — present if backend includes trace context in SSE
  trace_id?: string;
  langfuse_trace_url?: string;
}

/**
 * Accumulated state produced by the SSE reducer (lib/sse.ts).
 * Drives AgentTrace UI.
 */
export interface AgentTraceState {
  events: SSEEnvelope[];
  status: 'idle' | 'connecting' | 'streaming' | 'done' | 'error';
  errorMessage?: string;
  traceId?: string;
}
