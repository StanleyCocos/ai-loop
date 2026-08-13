import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ai-loop dashboard",
  description: "Visual control center for ai-loop tasks, logs, and artifacts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
