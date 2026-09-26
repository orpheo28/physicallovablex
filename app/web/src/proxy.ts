import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, safeEqual, sessionToken } from "@/lib/session";

/**
 * 1. APP_PASSWORD (web password) — when set, every page and /backend/* need the session cookie set by /login.
 *    Pages redirect to /login?next=<original path + query>; API calls get a 401.
 * 2. API_SHARED_KEY — added server-side as `X-App-Key` on /backend/* before next.config.ts rewrites to the API.
 *    The browser never sees either secret.
 */
export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const password = process.env.APP_PASSWORD;
  const isLogin = pathname === "/login" || pathname === "/auth/login";

  if (password && !isLogin) {
    const cookie = request.cookies.get(SESSION_COOKIE)?.value;
    if (!cookie || !safeEqual(cookie, await sessionToken(password))) {
      if (pathname.startsWith("/backend/") || pathname === "/file-status") {
        return NextResponse.json({ detail: "Sign in required." }, { status: 401 });
      }
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.search = `?next=${encodeURIComponent(pathname + search)}`;
      return NextResponse.redirect(url);
    }
  }

  const key = process.env.API_SHARED_KEY;
  if (key && pathname.startsWith("/backend/")) {
    const headers = new Headers(request.headers);
    headers.set("X-App-Key", key);
    headers.delete("cookie"); // the web session cookie is for the web app only
    return NextResponse.next({ request: { headers } });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|icon.svg|favicon.ico).*)"],
};
