import type { Metadata } from "next";
import { projectName } from "@/lib/serverMeta";

export async function generateMetadata({ params }: LayoutProps<"/projects/[id]/wow">): Promise<Metadata> {
  const { id } = await params;
  return { title: `Overview — ${await projectName(id)}` };
}

export default function WowLayout({ children }: LayoutProps<"/projects/[id]/wow">) {
  return children;
}
