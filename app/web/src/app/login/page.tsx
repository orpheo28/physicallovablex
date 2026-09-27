import type { Metadata } from "next";
import { Lockup } from "@/components/Lockup";
import { safeNext } from "@/lib/session";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const sp = await searchParams;
  const next = safeNext(typeof sp.next === "string" ? sp.next : "/");
  const error = sp.error === "1";
  return (
    <div className="flex h-full items-center justify-center px-6 pb-12">
      <form method="post" action="/auth/login" className="w-full max-w-[380px] rounded-lg bg-surface p-8 shadow-float">
        <Lockup />
        <h1 className="title mt-6 text-xl">Private demo</h1>
        <p className="mt-2 text-base text-ink-2">Enter the password you were given to open the demo.</p>
        <input type="hidden" name="next" value={next} />
        <label className="mt-6 flex flex-col gap-2">
          <span className="micro">Password</span>
          <input name="password" type="password" required autoFocus autoComplete="current-password" className="field" aria-invalid={error} />
        </label>
        {error && (
          <p role="alert" className="mt-3 text-sm text-danger">
            Wrong password. Try again.
          </p>
        )}
        <button
          type="submit"
          className="mt-6 inline-flex h-10 w-full items-center justify-center rounded border border-accent bg-accent px-4 text-base font-medium text-ink transition-colors duration-150 hover:border-[#ff6a26] hover:bg-[#ff6a26]"
        >
          Open the demo
        </button>
        <p className="mt-4 text-sm text-ink-3">You stay signed in on this browser for 7 days.</p>
      </form>
    </div>
  );
}
