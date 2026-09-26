import type { Metadata } from "next";
import Link from "next/link";
import { Archivo, Geist_Mono, Inter_Tight } from "next/font/google";
import { Legend } from "@/components/Legend";
import { Nav } from "@/components/Nav";
import { Mark } from "@/components/Mark";
import "./globals.css";

const ui = Inter_Tight({ variable: "--font-ui", subsets: ["latin"], display: "swap" });
const num = Geist_Mono({ variable: "--font-num", subsets: ["latin"], display: "swap" });
// Condensed display face (Archivo, width axis) — page titles and the overview product name only.
const display = Archivo({ variable: "--font-display-face", subsets: ["latin"], display: "swap", axes: ["wdth"] });

export const metadata: Metadata = {
  title: { default: "PhysicalLovableX — From idea to 1,000 units shipped", template: "%s · PhysicalLovableX" },
  description: "Turn a plain-language product idea into a Factory Pack any factory can quote: design, CAD, DFM, costs, factories, logistics.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${ui.variable} ${num.variable} ${display.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded focus:bg-ink focus:px-3 focus:py-1.5 focus:text-white">
          Skip to content
        </a>
        <header data-chrome className="sticky top-0 z-30 border-b border-line bg-paper/90 backdrop-blur-[6px]">
          <div className="mx-auto flex h-14 max-w-[1320px] items-center gap-8 px-6 lg:px-10">
            <Link href="/" className="flex items-center gap-2.5 text-base font-semibold tracking-[-0.01em]">
              <Mark />
              PhysicalLovableX
            </Link>
            <Nav />
            <span className="ml-auto hidden items-center gap-2 text-sm text-ink-3 md:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-fictional" aria-hidden />
              Demo · simulated factory network
            </span>
          </div>
        </header>
        <main id="main" className="flex-1">
          {children}
        </main>
        <footer data-chrome className="mt-16 border-t border-line">
          <div className="mx-auto flex max-w-[1320px] flex-col gap-4 px-6 py-8 lg:px-10">
            <Legend />
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-sm text-ink-2">
              <p>Demo built for a case study. All factories, quotes and freight rates are fictional demo data. No real personal data is stored.</p>
              <p className="flex items-center gap-4 text-ink-3">
                <Link href="/about" className="transition-colors hover:text-ink">
                  About
                </Link>
                <span className="flex items-center gap-2">
                  <Mark size={10} /> PhysicalLovableX
                </span>
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
