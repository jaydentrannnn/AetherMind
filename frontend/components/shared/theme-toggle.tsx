"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle(): JSX.Element {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <button className="rounded-md border px-2 py-1 text-xs">Theme</button>;
  }

  const isDark = resolvedTheme !== "light";
  return (
    <button
      className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-1 text-xs"
      data-testid="theme-toggle"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      type="button"
    >
      <span className="inline-flex items-center gap-1">
        {isDark ? <Sun size={14} /> : <Moon size={14} />}
        {isDark ? "Light" : "Dark"}
      </span>
    </button>
  );
}
