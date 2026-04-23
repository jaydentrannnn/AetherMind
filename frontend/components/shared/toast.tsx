"use client";

import type { ToastItem } from "./use-toasts";

export function Toasts({ toasts }: { toasts: ToastItem[] }): JSX.Element {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          className={`rounded-md border px-3 py-2 text-sm shadow ${toast.type === "success" ? "border-[var(--verified)] bg-[var(--verified-bg)] text-[var(--verified)]" : "border-[var(--blocked)] bg-[var(--blocked-bg)] text-[var(--blocked)]"}`}
          key={toast.id}
        >
          {toast.msg}
        </div>
      ))}
    </div>
  );
}
