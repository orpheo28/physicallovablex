import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocPage } from "@/components/docs/DocPage";
import { docPages } from "@/lib/docs";

export const metadata: Metadata = { title: "Overview" };

export default function DocsHome() {
  const page = docPages().find((p) => p.slug === "overview") ?? docPages()[0];
  if (!page) notFound();
  return <DocPage page={page} />;
}
