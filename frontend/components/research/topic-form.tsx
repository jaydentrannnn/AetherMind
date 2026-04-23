"use client";

import { Spinner } from "@/components/shared";

interface TopicFormProps {
  topic: string;
  submitting: boolean;
  onTopicChange: (value: string) => void;
  onSubmit: () => void;
}

export function TopicForm({
  topic,
  submitting,
  onTopicChange,
  onSubmit,
}: TopicFormProps): JSX.Element {
  return (
    <div className="topic-form rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-4">
      <textarea
        className="h-40 w-full rounded-md border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-3"
        data-testid="topic-input"
        onChange={(event) => onTopicChange(event.target.value)}
        placeholder="What would you like to research?"
        value={topic}
      />
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-[var(--text-dim)]">Ctrl+Enter to submit</span>
        <button
          className="btn-accent inline-flex items-center gap-2 rounded-md px-4 py-2"
          data-testid="submit-research"
          disabled={submitting || !topic.trim()}
          onClick={onSubmit}
          type="button"
        >
          {submitting ? <Spinner size={14} /> : null}
          {submitting ? "Starting..." : "Start Research"}
        </button>
      </div>
    </div>
  );
}
