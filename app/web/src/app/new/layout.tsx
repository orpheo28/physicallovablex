import type { Metadata } from "next";

export const metadata: Metadata = { title: "New project" };

export default function NewLayout({ children }: LayoutProps<"/new">) {
  return children;
}
