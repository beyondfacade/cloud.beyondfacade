import { NextResponse, type NextRequest } from "next/server";
import { ADMIN_SESSION_COOKIE, adminGateRedirect } from "@/shared/admin-gate";

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const target = adminGateRedirect(pathname, search, request.cookies.has(ADMIN_SESSION_COOKIE));
  return target ? NextResponse.redirect(new URL(target, request.url)) : NextResponse.next();
}

export const config = { matcher: ["/admin", "/admin/:path*"] };
