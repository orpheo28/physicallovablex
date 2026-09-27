import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocPage, pageTitle } from "@/components/docs/DocPage";
import { docPages } from "@/lib/docs";

// Every page is generated at build time from web/content/docs; unknown slugs are 404s.
export const dynamicParams = false;

export function generateStaticParams() {
  return docPages().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: PageProps<"/docs/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const page = docPages().find((p) => p.slug === slug);
  return { title: page ? pageTitle(page) : "Not found" };
}

export default async function DocsSlug({ params }: PageProps<"/docs/[slug]">) {
  const { slug } = await params;
  const page = docPages().find((p) => p.slug === slug);
  if (!page) notFound();
  return <DocPage page={page} />;
}
