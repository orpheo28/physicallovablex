import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-24 lg:px-10">
      <p className="font-mono text-sm text-ink-3">404</p>
      <h1 className="mt-3 title text-[28px] leading-[34px]">This page does not exist.</h1>
      <p className="mt-2 text-md text-ink-2">Check the address, or go back to your projects.</p>
      <Link href="/projects" className="mt-6 inline-flex h-8 items-center rounded border border-line-2 bg-surface px-3 text-sm font-medium hover:border-ink-4">
        Open projects
      </Link>
    </div>
  );
}
