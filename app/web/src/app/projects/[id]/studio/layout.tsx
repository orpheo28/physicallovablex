import type { Metadata } from "next";
import { projectName } from "@/lib/serverMeta";

export async function generateMetadata({ params }: LayoutProps<"/projects/[id]/studio">): Promise<Metadata> {
  const { id } = await params;
  return { title: `Studio — ${await projectName(id)}` };
}

export default function StudioLayout({ children }: LayoutProps<"/projects/[id]/studio">) {
  return children;
}
