import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ScholarScope",
  description: "Map the research landscape of any topic.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-ink-800 bg-ink-900/60 backdrop-blur sticky top-0 z-20">
            <div className="mx-auto max-w-6xl px-6 py-3 flex items-center gap-3">
              <Link href="/" className="flex items-center gap-2 group">
                <span className="text-accent text-lg">◆</span>
                <span className="font-semibold tracking-tight group-hover:text-accent-soft transition-colors">
                  ScholarScope
                </span>
              </Link>
              <span className="text-xs text-slate-500 ml-2 hidden sm:inline">
                research landscape discovery
              </span>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
