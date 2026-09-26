import { NextResponse } from "next/server";
import { SESSION_COOKIE, SESSION_MAX_AGE, safeEqual, safeNext, sessionToken } from "@/lib/session";

/** POST (form) → compares with APP_PASSWORD, sets the 7-day httpOnly session cookie, redirects to `next`. */
export async function POST(request: Request) {
  const form = await request.formData();
  const next = safeNext(String(form.get("next") ?? "/"));
  const password = process.env.APP_PASSWORD;
  const url = new URL(request.url);
  if (!password) return NextResponse.redirect(new URL(next, url), 303);

  const given = String(form.get("password") ?? "");
  if (!safeEqual(await sessionToken(given), await sessionToken(password))) {
    const back = new URL("/login", url);
    back.searchParams.set("next", next);
    back.searchParams.set("error", "1");
    return NextResponse.redirect(back, 303);
  }
  const res = NextResponse.redirect(new URL(next, url), 303);
  res.cookies.set(SESSION_COOKIE, await sessionToken(password), {
    httpOnly: true,
    sameSite: "lax",
    secure: url.protocol === "https:",
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return res;
}
