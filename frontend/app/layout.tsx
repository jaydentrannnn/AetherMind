import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
