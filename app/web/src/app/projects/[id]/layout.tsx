import type { Metadata } from "next";
import { projectName } from "@/lib/serverMeta";
import { ProjectShell } from "@/components/project/ProjectShell";

export async function generateMetadata({ params }: LayoutProps<"/projects/[id]">): Promise<Metadata> {
  const { id } = await params;
  return { title: await projectName(id) };
}

export default async function ProjectLayout({ children, params }: LayoutProps<"/projects/[id]">) {
  const { id } = await params;
  return <ProjectShell id={id}>{children}</ProjectShell>;
}
