import type { Metadata } from "next";
import { projectName } from "@/lib/serverMeta";

export async function generateMetadata({ params }: LayoutProps<"/projects/[id]">): Promise<Metadata> {
  const { id } = await params;
  return { title: await projectName(id) };
}

export default function ProjectLayout({ children }: LayoutProps<"/projects/[id]">) {
  return children;
}
