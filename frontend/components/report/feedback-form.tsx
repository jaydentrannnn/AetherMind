"use client";

import { useState } from "react";
import { submitFeedbackOptimistic } from "@/lib/api";
import type { UUID } from "@/lib/types";

export function FeedbackForm({ reportId }: { reportId: UUID }): JSX.Element {
  const [accepted, setAccepted] = useState(true);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const submit = async (): Promise<void> => {
    setStatus("saving");
    const result = await submitFeedbackOptimistic(
      { report_id: reportId, accepted, user_comment: comment },
      {
        onError: () => setStatus("error"),
      },
    );
    setStatus(result ? "saved" : "error");
  };

  return (
    <div className="space-y-3 rounded border p-3">
      <div className="flex items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          <input checked={accepted} onChange={(e) => setAccepted(e.target.checked)} type="checkbox" />
          Accept report
        </label>
      </div>
      <textarea
        className="w-full rounded border bg-[var(--surface)] p-2"
        onChange={(e) => setComment(e.target.value)}
        placeholder="Share what should improve"
        value={comment}
      />
      <button className="btn-accent rounded px-3 py-2 text-sm" data-testid="feedback-submit" disabled={status === "saving"} onClick={submit} type="button">
        {status === "saving" ? "Saving..." : "Submit feedback"}
      </button>
      {status === "saved" && <p className="text-xs text-verified">Feedback submitted.</p>}
      {status === "error" && <p className="text-xs text-blocked">Feedback failed. Try again.</p>}
    </div>
  );
}
