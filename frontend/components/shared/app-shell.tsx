import type { ReactNode } from "react";
import { TopNav } from "./top-nav";

export function AppShell({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="app-shell min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <TopNav />
      <main className="app-main mx-auto w-full max-w-7xl p-6">{children}</main>
    </div>
  );
}
