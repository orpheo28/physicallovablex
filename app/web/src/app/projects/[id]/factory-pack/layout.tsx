import type { Metadata } from "next";
import { projectName } from "@/lib/serverMeta";

export async function generateMetadata({ params }: LayoutProps<"/projects/[id]/factory-pack">): Promise<Metadata> {
  const { id } = await params;
  return { title: `Factory Pack — ${await projectName(id)}` };
}

export default function FactoryPackLayout({ children }: LayoutProps<"/projects/[id]/factory-pack">) {
  return children;
}
