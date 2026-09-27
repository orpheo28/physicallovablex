import type { Metadata } from "next";

export const metadata: Metadata = { title: "Examples" };

export default function ExamplesLayout({ children }: LayoutProps<"/examples">) {
  return children;
}
