/** 개발 서버 백엔드 프록시 — 브라우저는 프론트 origin(3200)만 호출하고, Next 서버가 백엔드로 전달한다.
 *  원격 개발(VS Code Remote-SSH 포트 포워딩 등)에서 브라우저가 서버의 127.0.0.1:8201에 직접 닿지 못하는 문제를 없앤다.
 *  BACKEND_ORIGIN(서버 전용 env)이 없으면 규칙을 만들지 않는다 — Vercel·mock 기본 동작 무변경. */
export const BACKEND_PROXY_PREFIX = "/api/backend";

export function backendProxyRewrites(origin: string | undefined) {
  if (!origin) return [];
  return [{ source: `${BACKEND_PROXY_PREFIX}/:path*`, destination: `${origin.replace(/\/+$/, "")}/:path*` }];
}
