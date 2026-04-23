import type { Metadata } from "next";
import "./globals.css";
import { AppShell, ThemeProvider } from "@/components/shared";

export const metadata: Metadata = {
  title: "AetherMind",
  description: "Agentic research and report generator",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false}>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
