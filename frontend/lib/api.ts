/**
 * lib/api.ts
 *
 * Typed fetch helpers for the AetherMind FastAPI backend.
 * Base URL: process.env.NEXT_PUBLIC_API_BASE_URL
 *
 * Usage:
 *   import { api } from '@/lib/api';
 *   const { job_id } = await api.createResearch({ topic: '...' });
 *
 * All responses are runtime-validated with Zod.
 * Confirm schemas against GET /openapi.json before releasing.
 *
 * Versioned: v1 — April 2026
 */

import { z } from 'zod';
import type {
  CreateResearchRequest,
  CreateResearchResponse,
  Report,
  ReportVersionMeta,
  ResearchJobSummary,
  FeedbackRequest,
  FeedbackResponse,
  MemoryPreferences,
  MemorySearchResponse,
  UUID,
} from './types';


// ─── Config ───────────────────────────────────────────────────────────────────

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';


// ─── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    public readonly requestId?: string,
    message?: string,
  ) {
    super(message ?? `API error ${status}`);
    this.name = 'ApiError';
  }
}


// ─── Zod schemas ─────────────────────────────────────────────────────────────
// Partial validation: confirm field-level shapes against OpenAPI before v1 launch.

const SourceSchema = z.object({
  id:       z.string(),
  title:    z.string(),
  url:      z.string().url(),
  domain:   z.string(),
  snippet:  z.string().optional(),
  verified: z.boolean(),
  type:     z.enum(['web', 'arxiv', 'pdf', 'url', 'code']),
});

const CitationSchema = z.object({
  source_id: z.string(),
  snippet:   z.string().optional(),
  verified:  z.boolean(),
});

const GuardrailViolationSchema = z.object({
  claim:      z.string(),
  rationale:  z.string(),
  source_ids: z.array(z.string()).optional(),
});

const GuardrailReportSchema = z.object({
  unverified_claims:  z.array(GuardrailViolationSchema),
  policy_violations:  z.array(GuardrailViolationSchema),
  closure_violations: z.array(GuardrailViolationSchema),
});

const RubricDimensionSchema = z.object({
  score:     z.number(),
  max:       z.number(),
  label:     z.string(),
  rationale: z.string().optional(),
});

const RubricSchema = z.record(z.string(), RubricDimensionSchema);

const ContentBlockSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('p'),     text: z.string(), citations: z.array(z.string()).optional() }),
  z.object({ type: z.literal('ul'),    items: z.array(z.string()), citations: z.array(z.string()).optional() }),
  z.object({ type: z.literal('ol'),    items: z.array(z.string()), citations: z.array(z.string()).optional() }),
  z.object({ type: z.literal('code'),  text: z.string(), language: z.string().optional() }),
  z.object({ type: z.literal('table'), headers: z.array(z.string()), rows: z.array(z.array(z.string())), citations: z.array(z.string()).optional() }),
]);

const ReportSectionSchema = z.object({
  id:      z.string().optional(),
  title:   z.string(),
  content: z.union([z.array(ContentBlockSchema), z.string()]),
});

const ReportVersionMetaSchema = z.object({
  id:           z.string(),
  created_at:   z.string(),
  label:        z.string(),
  summary_diff: z.string().optional(),
});

const ReportSchema = z.object({
  id:         z.string(),
  job_id:     z.string(),
  title:      z.string(),
  summary:    z.string().optional(),
  markdown:   z.string().optional(),
  sections:   z.array(ReportSectionSchema),
  sources:    z.array(SourceSchema),
  guardrails: GuardrailReportSchema.optional(),
  rubric:     RubricSchema.optional(),
  versions:   z.array(ReportVersionMetaSchema).optional(),
  depth:      z.enum(['quick', 'standard', 'deep']),
  created_at: z.string(),
  trace_id:   z.string().optional(),
  request_id: z.string().optional(),
});

const ResearchJobSummarySchema = z.object({
  job_id: z.string(),
  topic: z.string(),
  status: z.string(),
  created_at: z.string(),
  latest_report_id: z.string().nullable(),
});

const CreateResearchResponseSchema = z.object({ job_id: z.string() });
const FeedbackResponseSchema = z.object({ id: z.string(), created_at: z.string() });

const PreferenceSchema = z.object({
  key:       z.string(),
  value:     z.string(),
  source:    z.enum(['user', 'inferred']),
  updatedAt: z.string(),
});
const MemoryPreferencesSchema = z.object({
  preferences:    z.array(PreferenceSchema),
  allow_domains:  z.array(z.string()),
  deny_domains:   z.array(z.string()),
});

const RecalledMemorySchema = z.object({
  id:        z.string(),
  title:     z.string(),
  snippet:   z.string(),
  score:     z.number(),
  date:      z.string(),
  report_id: z.string().optional(),
});
const MemorySearchResponseSchema = z.object({
  results: z.array(RecalledMemorySchema),
  query:   z.string(),
});


// ─── Core fetch wrapper ───────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit & { schema: z.ZodType<T> },
): Promise<T> {
  const { schema, ...init } = options;

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...((init.headers as Record<string, string>) ?? {}),
    },
    ...init,
  });

  const requestId = res.headers.get('x-request-id') ?? undefined;

  if (!res.ok) {
    let body: unknown;
    try { body = await res.json(); } catch { body = await res.text(); }
    throw new ApiError(res.status, body, requestId);
  }

  const json = await res.json();

  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    // Log validation errors without crashing — fail-open with raw data
    console.warn('[api] Response validation failed:', parsed.error.flatten());
    // Return the raw data cast — confirm schema with OpenAPI before hardening this
    return json as T;
  }

  return parsed.data;
}


// ─── API surface ─────────────────────────────────────────────────────────────

export const api = {

  /** POST /research — submit a new research job */
  createResearch: (req: CreateResearchRequest): Promise<CreateResearchResponse> =>
    apiFetch('/research', {
      method: 'POST',
      body: JSON.stringify(req),
      schema: CreateResearchResponseSchema,
    }),

  /** GET /reports — list recent research jobs for the default user */
  getReportsList: (limit = 50): Promise<ResearchJobSummary[]> =>
    apiFetch(`/reports?limit=${encodeURIComponent(String(limit))}`, {
      method: 'GET',
      schema: z.array(ResearchJobSummarySchema),
    }),

  /** GET /reports/{id} — fetch a complete report */
  getReport: (id: UUID): Promise<Report> =>
    apiFetch(`/reports/${id}`, { method: 'GET', schema: ReportSchema }),

  /** GET /reports/{id}/versions — list version metadata */
  getReportVersions: (id: UUID): Promise<ReportVersionMeta[]> =>
    apiFetch(`/reports/${id}/versions`, {
      method: 'GET',
      schema: z.array(ReportVersionMetaSchema),
    }),

  /** POST /feedback */
  submitFeedback: (req: FeedbackRequest): Promise<FeedbackResponse> =>
    apiFetch('/feedback', {
      method: 'POST',
      body: JSON.stringify(req),
      schema: FeedbackResponseSchema,
    }),

  /** GET /memory/preferences */
  getPreferences: (): Promise<MemoryPreferences> =>
    apiFetch('/memory/preferences', { method: 'GET', schema: MemoryPreferencesSchema }),

  /** POST /memory/preferences */
  savePreferences: (prefs: MemoryPreferences): Promise<MemoryPreferences> =>
    apiFetch('/memory/preferences', {
      method: 'POST',
      body: JSON.stringify(prefs),
      schema: MemoryPreferencesSchema,
    }),

  /** GET /memory/search?q= */
  searchMemory: (query: string): Promise<MemorySearchResponse> =>
    apiFetch(`/memory/search?q=${encodeURIComponent(query)}`, {
      method: 'GET',
      schema: MemorySearchResponseSchema,
    }),

} as const;


// ─── Optimistic feedback helper ───────────────────────────────────────────────

/**
 * Submit feedback with optimistic UI + reconcile on failure.
 *
 * Usage:
 *   const result = await submitFeedbackOptimistic(req, {
 *     onOptimistic: () => setFeedbackState('accepted'),
 *     onError:      () => setFeedbackState(null), // revert
 *   });
 */
export async function submitFeedbackOptimistic(
  req: FeedbackRequest,
  callbacks: {
    onOptimistic?: () => void;
    onSuccess?: (res: FeedbackResponse) => void;
    onError?: (err: ApiError) => void;
  },
): Promise<FeedbackResponse | null> {
  callbacks.onOptimistic?.();
  try {
    const res = await api.submitFeedback(req);
    callbacks.onSuccess?.(res);
    return res;
  } catch (err) {
    // Reconcile: revert optimistic state
    callbacks.onError?.(err instanceof ApiError ? err : new ApiError(0, err));
    return null;
  }
}
