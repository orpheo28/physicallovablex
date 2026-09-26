import type { Metadata } from "next";

export const metadata: Metadata = { title: "Projects" };

export default function ProjectsLayout({ children }: LayoutProps<"/projects">) {
  return children;
}
