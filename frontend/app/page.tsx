"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AdvancedOptions } from "@/components/research/advanced-options";
import { RecentResearchList } from "@/components/research/recent-research-list";
import { TopicForm } from "@/components/research/topic-form";
import { api } from "@/lib/api";

export default function HomePage(): JSX.Element {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");
  const [tools, setTools] = useState({ web: true, arxiv: true, pdf: true, url: false, code: false });
  const [domains, setDomains] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (): Promise<void> => {
    if (!topic.trim()) return;
    setSubmitting(true);
    try {
      const response = await api.createResearch({
        topic,
        options: {
          depth,
          tools,
          preferred_domains: domains,
        },
      });
      router.push(`/reports/${response.job_id}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="mx-auto max-w-4xl space-y-4">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--accent-subtle)] bg-[var(--accent-bg)] px-3 py-1 text-xs text-[var(--accent-token)]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--accent-token)]" />
          AetherMind Research Agent
        </div>
        <h1 className="text-3xl font-semibold">What would you like to research?</h1>
        <p className="text-sm text-[var(--text-muted)]">
          The agent plans sub-questions, gathers evidence, synthesizes a report, and verifies citations.
        </p>
      </div>
      <TopicForm onSubmit={submit} onTopicChange={setTopic} submitting={submitting} topic={topic} />
      <AdvancedOptions
        depth={depth}
        domains={domains}
        onDepthChange={setDepth}
        onDomainsChange={setDomains}
        onToolsChange={setTools}
        tools={tools}
      />
      <RecentResearchList />
    </section>
  );
}
