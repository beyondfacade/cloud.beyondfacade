import { safeNext } from "@/shared/auth/session";
import { MOCK_STATE, oauthCookie, redirect } from "../oauth";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const next = safeNext(url.searchParams.get("next"));
  const callback = `${url.pathname.replace(/\/start$/, "/callback")}?code=mock-code&state=${MOCK_STATE}`;
  return redirect(callback, [oauthCookie(`${MOCK_STATE}.${encodeURIComponent(next)}`)]);
}
