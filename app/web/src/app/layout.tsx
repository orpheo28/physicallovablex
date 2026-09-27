import type { Metadata } from "next";
import { Archivo, Geist_Mono, Inter_Tight } from "next/font/google";
import { AppFrame } from "@/components/AppFrame";
import "./globals.css";

const ui = Inter_Tight({ variable: "--font-ui", subsets: ["latin"], display: "swap" });
const num = Geist_Mono({ variable: "--font-num", subsets: ["latin"], display: "swap" });
// Condensed display face (Archivo, width axis) — page titles and the overview product name only.
const display = Archivo({ variable: "--font-display-face", subsets: ["latin"], display: "swap", axes: ["wdth"] });

export const metadata: Metadata = {
  title: { default: "PhysicalLovableX — From idea to 1,000 units shipped", template: "%s · PhysicalLovableX" },
  description: "Turn a plain-language product idea into a Factory Pack any factory can quote: design, CAD, DFM, costs, factories, logistics.",
};

/**
 * Desktop app shell (100dvh, the body never scrolls): top bar · main panel · status bar — see AppFrame.
 * Public docs (/docs) are documents: no gate, normal page scroll.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${ui.variable} ${num.variable} ${display.variable} h-full`}>
      <body className="h-dvh overflow-hidden">
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
