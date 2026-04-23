"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";

export function TopNav(): JSX.Element {
  const pathname = usePathname();

  return (
    <header className="flex h-[var(--nav-h)] items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--surface)] px-5">
      <div className="flex items-center gap-5">
        <Link className="flex items-center gap-2 font-semibold" href="/">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-[var(--accent-bg)] text-[var(--accent-token)]">
            A
          </span>
          AetherMind
        </Link>
        <nav className="flex items-center gap-2 text-sm">
          <Link
            className={`rounded-md px-3 py-1 ${pathname === "/" ? "bg-[var(--surface-raised)]" : ""}`}
            href="/"
          >
            Research
          </Link>
          <Link
            className={`rounded-md px-3 py-1 ${pathname === "/reports" || pathname.startsWith("/reports/") ? "bg-[var(--surface-raised)]" : ""}`}
            href="/reports"
          >
            Reports
          </Link>
          <Link
            className={`rounded-md px-3 py-1 ${pathname === "/memory" ? "bg-[var(--surface-raised)]" : ""}`}
            href="/memory"
          >
            Memory
          </Link>
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-1 text-xs text-[var(--text-muted)] md:inline-flex">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--verified)]" />
          API connected
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
