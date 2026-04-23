import type { Page } from "@playwright/test";

const MOCK_REPORT = {
  id: "r-1",
  job_id: "j-test",
  title: "Mock Report",
  summary: "Summary",
  markdown: "## Findings\n\nEvidence-backed summary.",
  sections: [],
  sources: [
    {
      id: "src-1",
      title: "Paper A",
      url: "https://arxiv.org/abs/1234.5678",
      domain: "arxiv.org",
      snippet: "Supportive snippet",
      verified: true,
      type: "arxiv",
    },
  ],
  guardrails: { unverified_claims: [], policy_violations: [], closure_violations: [] },
  rubric: {},
  versions: [{ id: "v1", created_at: "2026-04-22T00:00:00Z", label: "v1", summary_diff: "initial" }],
  depth: "standard",
  created_at: "2026-04-22T00:00:00Z",
  trace_id: "trace-123",
  request_id: "req-456",
};

const MOCK_PREFERENCES = {
  preferences: [{ key: "tone", value: "concise", source: "user", updatedAt: "2026-04-22" }],
  allow_domains: ["arxiv.org"],
  deny_domains: ["spam.example"],
};

const SSE_BODY = [
  'data: {"type":"planner","msg":"Planned sub-questions"}',
  'data: {"type":"researcher","msg":"Gathering evidence"}',
  'data: {"type":"tool","msg":"web_search complete"}',
  'data: {"type":"synthesizer","msg":"Draft generated"}',
  'data: {"type":"guardrails","msg":"All checks passed"}',
  'data: {"type":"critic","msg":"Approved"}',
  "data: [DONE]",
  "",
].join("\n");

export async function setupApiMocks(page: Page): Promise<void> {
  await page.route("**/research", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job_id: "j-test" }),
      });
      return;
    }
    await route.continue();
  });

  await page.route("**/research/*/stream", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: SSE_BODY,
    });
  });

  await page.route("**/reports/*/versions", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_REPORT.versions),
    });
  });

  await page.route("**/reports/*", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_REPORT),
    });
  });

  await page.route("**/feedback", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "f-1", created_at: "2026-04-22T00:00:00Z" }),
    });
  });

  await page.route("**/memory/preferences", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_PREFERENCES),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_PREFERENCES),
    });
  });

  await page.route("**/memory/search**", async (route) => {
    if (!route.request().url().includes(":8000/")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: "attention",
        results: [{ id: "m1", title: "Attention report", snippet: "Context", score: 0.92, date: "2026-04-20" }],
      }),
    });
  });
}

export function mockReport(): typeof MOCK_REPORT {
  return MOCK_REPORT;
}

export function mockPreferences(): typeof MOCK_PREFERENCES {
  return MOCK_PREFERENCES;
}
