import type { Metadata } from "next";
import { JetBrains_Mono, Playfair_Display, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const display = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600", "700", "800", "900"],
  style: ["normal", "italic"],
});
const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ScholarScope — Research Landscape Discovery",
  description: "Map the research landscape of any topic.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${serif.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-foreground focus:px-4 focus:py-2 focus:font-mono focus:text-xs focus:uppercase focus:tracking-widest focus:text-background"
        >
          Skip to content
        </a>

        <header className="border-b-4 border-foreground">
          <div className="mx-auto flex max-w-editorial items-end justify-between px-6 py-6 md:px-8 lg:px-12">
            <Link
              href="/"
              className="group focus-visible:outline-none"
              aria-label="ScholarScope home"
            >
              <span className="block font-display text-3xl font-black leading-none tracking-tighter transition-none group-hover:italic md:text-4xl">
                ScholarScope
              </span>
            </Link>
            <span className="hidden font-mono text-xs uppercase tracking-widest text-secondary sm:block">
              Research Landscape Discovery
            </span>
          </div>
        </header>

        <main id="main" className="mx-auto max-w-editorial px-6 py-16 md:px-8 md:py-24 lg:px-12">
          {children}
        </main>

        <footer className="border-t-4 border-foreground">
          <div className="mx-auto flex max-w-editorial flex-col gap-1 px-6 py-8 font-mono text-xs uppercase tracking-widest text-secondary md:flex-row md:items-center md:justify-between md:px-8 lg:px-12">
            <span>ScholarScope</span>
            <span>Hybrid Retrieval · Reranking · LLM Synthesis</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
