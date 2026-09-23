# 프론트엔드 MVP 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 지도 탐색 + AI 분석 탭 2개로 구성된 Metabole 웹 프론트엔드 MVP를 mock API 기반으로 완성한다 (백엔드 전환은 env 1개 변경).

**Architecture:** Next.js App Router에서 `app/`은 라우팅 셸만 담당하고, 기능은 `features/{map-explorer,agent-report}` 수직 분할, 횡단은 `shared/`. 백엔드 준비 전까지 Next.js Route Handler(`/api/mock/*`)가 스펙 §4 계약 그대로 mock을 서빙한다. 모든 색은 시맨틱 CSS 토큰(라이트 기본 + `data-theme="dark"` 토글).

**Tech Stack:** Next.js(App Router)+TypeScript(strict), Tailwind CSS v4, MapLibre GL, TanStack Query v5, react-markdown, Vitest+Testing Library, agent-browser(E2E·스크린샷)

**Spec:** `docs/superpowers/specs/2026-08-25-frontend-design.md`

## Global Constraints

- 모든 색상은 `styles/tokens.css`의 시맨틱 토큰 변수로만 사용 — 컴포넌트 내 hex/rgb 하드코딩 금지
- feature 간 직접 import 금지 — 통신은 URL 쿼리(`region`, `industry`, `year`, `metric`)와 `shared/`만
- 서버 상태는 TanStack Query만 사용 — Redux/Zustand 등 전역 상태 라이브러리 도입 금지
- API 베이스는 `NEXT_PUBLIC_API_BASE` env로만 접근 (`shared/config.ts` 경유) — 기본값 `/api/mock`
- 폰트: Pretendard, 숫자는 `tabular-nums`
- 금지: 보라 그라데이션, Inter/system 기본 폰트 스택, 쿠키커터 카드 그림자
- 브이월드 타일 키는 `NEXT_PUBLIC_VWORLD_KEY` (frontend/.env.local — git 커밋 금지, 이미 .gitignore 등록)
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- 각 태스크 완료 시 `frontend/docs/frontend_ver_log.md`는 마지막 태스크(Task 10)에서 일괄 기록

---

### Task 1: 스캐폴드 + 테스트 러너

**Files:**
- Create: `frontend/` 전체 (create-next-app), `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`, `frontend/src/shared/config.ts`
- Test: `frontend/src/shared/config.test.ts`

**Interfaces:**
- Produces: `config.apiBase: string` (`shared/config.ts`) — 이후 모든 API 호출이 사용

- [ ] **Step 1: Next.js 앱 생성 + 의존성 설치**

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/frontend
# 기존 파일 보존을 위해 임시 디렉토리에 생성 후 이동
npx create-next-app@latest tmp-app --ts --tailwind --app --src-dir --no-eslint --import-alias "@/*" --use-npm --yes
rsync -a tmp-app/ ./ && rm -rf tmp-app
npm i @tanstack/react-query maplibre-gl react-markdown
npm i -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: vitest 설정 작성**

`frontend/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", globals: true },
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
});
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

`package.json` scripts에 추가: `"test": "vitest run", "test:watch": "vitest"`

- [ ] **Step 3: 실패하는 config 테스트 작성**

`frontend/src/shared/config.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { config } from "./config";

describe("config", () => {
  it("apiBase 기본값은 /api/mock", () => {
    expect(config.apiBase).toBe("/api/mock");
  });
});
```

- [ ] **Step 4: 테스트 실패 확인** — Run: `npm test` / Expected: FAIL ("./config" 없음)

- [ ] **Step 5: config 구현**

`frontend/src/shared/config.ts`:
```ts
export const config = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "/api/mock",
  vworldKey: process.env.NEXT_PUBLIC_VWORLD_KEY ?? "",
} as const;
```

- [ ] **Step 6: 테스트 통과 확인** — Run: `npm test` / Expected: PASS

- [ ] **Step 7: 빌드 확인 후 커밋**

```bash
npm run build
git add frontend/ && git commit -m "feat(frontend): Next.js 스캐폴드 + vitest + shared/config

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: 디자인 토큰 2벌 + 테마 토글

**Files:**
- Create: `frontend/src/styles/tokens.css`, `frontend/src/shared/ui/theme-toggle.tsx`
- Modify: `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`
- Test: `frontend/src/shared/ui/theme-toggle.test.tsx`

**Interfaces:**
- Produces: CSS 변수 `--bg-base --bg-surface --bg-raised --text-primary --text-secondary --border --accent --accent-fg --ok --warn --danger`; `<ThemeToggle />`; `document.documentElement`의 `data-theme` 속성(`"light" | "dark"`)

- [ ] **Step 1: 실패하는 토글 테스트 작성**

`frontend/src/shared/ui/theme-toggle.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./theme-toggle";

it("클릭 시 data-theme가 light↔dark 전환된다", async () => {
  document.documentElement.dataset.theme = "light";
  render(<ThemeToggle />);
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("dark");
  await userEvent.click(screen.getByRole("button", { name: /테마/ }));
  expect(document.documentElement.dataset.theme).toBe("light");
});
```

- [ ] **Step 2: 실패 확인** — Run: `npm test` / Expected: FAIL

- [ ] **Step 3: 토큰 + 토글 구현**

`frontend/src/styles/tokens.css` (라이트 기본, 다크는 `[data-theme="dark"]` 오버라이드):
```css
:root {
  --bg-base: #f7f7f5;      --bg-surface: #ffffff;   --bg-raised: #f0f0ee;
  --text-primary: #1a1a1a; --text-secondary: #5c5c57;
  --border: #e2e2de;
  --accent: #0f6b5c;       --accent-fg: #ffffff;    /* 임시 — Task 10 폴리시에서 확정 */
  --ok: #15803d;           --warn: #b45309;         --danger: #b91c1c;
}
[data-theme="dark"] {
  --bg-base: #16181a;      --bg-surface: #1e2124;   --bg-raised: #26292d;
  --text-primary: #f2f2f0; --text-secondary: #a3a39d;
  --border: #33373b;
  --accent: #2dd4bf;       --accent-fg: #10201d;
  --ok: #4ade80;           --warn: #fbbf24;         --danger: #f87171;
}
```

`frontend/src/shared/ui/theme-toggle.tsx`:
```tsx
"use client";
import { useCallback, useSyncExternalStore } from "react";

function getTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}
function subscribe(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "light");
  const toggle = useCallback(() => {
    document.documentElement.dataset.theme = getTheme() === "dark" ? "light" : "dark";
  }, []);
  return (
    <button aria-label="테마 전환" onClick={toggle}
      className="rounded-md border border-[var(--border)] px-2 py-1 text-sm text-[var(--text-secondary)]">
      {theme === "dark" ? "라이트" : "다크"}
    </button>
  );
}
```

`layout.tsx`: `<html lang="ko" data-theme="light">`, Pretendard CDN 링크(`https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.min.css`), body에 `bg-[var(--bg-base)] text-[var(--text-primary)]` + `font-feature-settings: "tnum"` 전역 적용. `globals.css`에서 `tokens.css` import.

- [ ] **Step 4: 통과 확인** — Run: `npm test` / Expected: PASS
- [ ] **Step 5: 시각 확인** — `npm run dev` 후 루트 페이지에서 토글 동작·양 테마 배경 전환 확인
- [ ] **Step 6: 커밋** — `git add frontend && git commit -m "feat(frontend): 시맨틱 디자인 토큰 2벌 + 테마 토글" (+Co-Authored-By)`

---

### Task 3: shared API 클라이언트 + 계약 타입

**Files:**
- Create: `frontend/src/shared/api/client.ts`, `frontend/src/shared/api/types.ts`, `frontend/src/shared/api/providers.tsx`
- Test: `frontend/src/shared/api/client.test.ts`

**Interfaces:**
- Produces:
  - `apiGet<T>(path: string): Promise<T>` — 실패 시 `ApiError {code, message}` throw
  - `apiPost<T>(path: string, body: unknown): Promise<T>`
  - types: `MetricRow {region_code: string; value: number}`, `RegionSummary {region_code; name; industry_id; cards: SummaryCard[]}`, `SummaryCard {label; value: string; grade: "fact" | "signal"}`, `AgentEvent`(유니언: `agent_status | tool_call | report_delta | report_done` — 스펙 §4 스키마 그대로), `MetricKey = "closure_rate" | "growth_rate" | "store_count"`
  - `<ApiProviders>` — QueryClientProvider 래퍼 (layout에서 사용)

- [ ] **Step 1: 실패하는 클라이언트 테스트**

`frontend/src/shared/api/client.test.ts`:
```ts
import { afterEach, expect, it, vi } from "vitest";
import { apiGet, ApiError } from "./client";

afterEach(() => vi.restoreAllMocks());

it("정상 응답은 JSON을 반환한다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
  await expect(apiGet("/x")).resolves.toEqual({ ok: 1 });
});

it("에러 응답은 {error:{code,message}}를 ApiError로 던진다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "없음" } }), { status: 404 })));
  await expect(apiGet("/x")).rejects.toMatchObject({ code: "NOT_FOUND", message: "없음" });
  await expect(apiGet("/x")).rejects.toBeInstanceOf(ApiError);
});
```

- [ ] **Step 2: 실패 확인** — Run: `npm test` / Expected: FAIL

- [ ] **Step 3: 구현**

`frontend/src/shared/api/client.ts`:
```ts
import { config } from "@/shared/config";

export class ApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>;
  const body = await res.json().catch(() => null);
  const err = body?.error ?? { code: `HTTP_${res.status}`, message: res.statusText };
  throw new ApiError(err.code, err.message);
}

export const apiGet = <T>(path: string) => fetch(`${config.apiBase}${path}`).then((r) => handle<T>(r));
export const apiPost = <T>(path: string, body: unknown) =>
  fetch(`${config.apiBase}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }).then((r) => handle<T>(r));
```

`types.ts`는 Interfaces 블록의 타입을 그대로 정의. `providers.tsx`:
```tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function ApiProviders({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } }));
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```
`layout.tsx` body를 `<ApiProviders>`로 감싼다.

- [ ] **Step 4: 통과 확인** — Run: `npm test` / Expected: PASS
- [ ] **Step 5: 커밋** — `"feat(frontend): API 클라이언트·계약 타입·QueryProvider"`

---

### Task 4: Mock API Route Handlers (스펙 §4 계약 그대로)

**Files:**
- Create: `frontend/src/app/api/mock/regions/geojson/route.ts`, `frontend/src/app/api/mock/metrics/route.ts`, `frontend/src/app/api/mock/regions/[code]/summary/route.ts`, `frontend/src/app/api/mock/analysis/route.ts`, `frontend/src/app/api/mock/analysis/[id]/events/route.ts`, `frontend/src/app/api/mock/fixtures.ts`
- Test: `frontend/src/app/api/mock/fixtures.test.ts`

**Interfaces:**
- Consumes: `MetricRow`, `RegionSummary`, `AgentEvent` (Task 3)
- Produces: §4 계약을 구현한 5개 엔드포인트. `fixtures.ts`가 export: `SEOUL_SAMPLE_GEOJSON`(강남권 실좌표 기반 행정동 폴리곤 8개, properties `{region_code, name}`), `metricRows(metric, year): MetricRow[]`, `summaryOf(code, industry): RegionSummary`, `agentEventScript(): AgentEvent[]`(agent_status·tool_call·report_delta 15건 + report_done 1건 시나리오 — **report_delta에 `section: "calculator"` 마크다운 표 포함: 월세vs매입 계산 결과. 스펙 §1 "계산기는 리포트 내 카드" 충족**)

- [ ] **Step 1: 실패하는 fixture 테스트**

```ts
import { expect, it } from "vitest";
import { SEOUL_SAMPLE_GEOJSON, metricRows, agentEventScript } from "./fixtures";

it("geojson feature마다 region_code·name이 있다", () => {
  expect(SEOUL_SAMPLE_GEOJSON.features.length).toBeGreaterThanOrEqual(8);
  for (const f of SEOUL_SAMPLE_GEOJSON.features)
    expect(f.properties).toMatchObject({ region_code: expect.any(String), name: expect.any(String) });
});
it("metricRows는 모든 feature의 region_code를 커버한다", () => {
  const codes = new Set(metricRows("closure_rate", 2026).map((r) => r.region_code));
  for (const f of SEOUL_SAMPLE_GEOJSON.features) expect(codes.has(f.properties!.region_code)).toBe(true);
});
it("이벤트 스크립트는 report_done으로 끝난다", () => {
  const script = agentEventScript();
  expect(script.at(-1)!.type).toBe("report_done");
});
```

- [ ] **Step 2: 실패 확인** — `npm test` FAIL
- [ ] **Step 3: fixtures + 핸들러 구현** — GET 3종은 `Response.json(...)`. SSE 핸들러:

```ts
// app/api/mock/analysis/[id]/events/route.ts
import { agentEventScript } from "../../fixtures";

export async function GET() {
  const script = agentEventScript();
  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      for (const ev of script) {
        controller.enqueue(enc.encode(`event: ${ev.type}\ndata: ${JSON.stringify(ev)}\n\n`));
        await new Promise((r) => setTimeout(r, 400)); // 진행 패널 시연용 지연
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  });
}
```
`POST /api/mock/analysis`는 `Response.json({ analysis_id: crypto.randomUUID() })`.

- [ ] **Step 4: 통과 확인** — `npm test` PASS, `curl localhost:3000/api/mock/metrics?metric=closure_rate` 형태 확인
- [ ] **Step 5: 커밋** — `"feat(frontend): mock API 라우트 (스펙 §4 계약)"`

---

### Task 5: 지도 탭 — MapLibre + 브이월드 타일 + 단계구분도

**Files:**
- Create: `frontend/src/features/map-explorer/components/map-view.tsx`, `frontend/src/features/map-explorer/lib/metric-color.ts`, `frontend/src/features/map-explorer/api.ts`, `frontend/src/features/map-explorer/hooks/use-map-data.ts`
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/src/features/map-explorer/lib/metric-color.test.ts`

**Interfaces:**
- Consumes: `apiGet`, `MetricRow`, `MetricKey`, config.vworldKey, CSS 토큰
- Produces:
  - `metricColor(value: number, domain: [number, number], scheme: "sequential" | "diverging"): string` — MapLibre fill-color용 hex 반환 (양 테마 공용, 색약 안전 스케일)
  - `<MapView regionCode, metric, industry, year, onSelectRegion(code)>`
  - `useMapData(metric, industry, year)` — `{geojson, rows}` TanStack Query 2개 (경계 staleTime Infinity)

- [ ] **Step 1: 실패하는 metricColor 테스트**

```ts
import { expect, it } from "vitest";
import { metricColor } from "./metric-color";

it("sequential: 도메인 하한→상한으로 갈수록 진해진다", () => {
  const lo = metricColor(0, [0, 1], "sequential");
  const hi = metricColor(1, [0, 1], "sequential");
  expect(lo).not.toBe(hi);
  expect(lo).toMatch(/^#[0-9a-f]{6}$/i);
});
it("도메인 밖 값은 경계값으로 클램프된다", () => {
  expect(metricColor(-5, [0, 1], "sequential")).toBe(metricColor(0, [0, 1], "sequential"));
});
it("diverging: 중앙값은 중립색이다", () => {
  const mid = metricColor(0.5, [0, 1], "diverging");
  expect(mid).toMatch(/^#[0-9a-f]{6}$/i);
});
```

- [ ] **Step 2: 실패 확인** — `npm test` FAIL
- [ ] **Step 3: 구현** — `metric-color.ts`: 색약 안전 스케일 보간 (sequential: `#fee8c8→#7f0000` 계열 5스톱, diverging: `#2166ac→#f7f7f7→#b2182b` 5스톱, RGB 선형 보간 + 클램프). `map-view.tsx`: maplibre-gl 초기화(서울 중심 [126.99, 37.55], zoom 11), 래스터 소스 = 브이월드 XYZ(`https://api.vworld.kr/req/wmts/1.0.0/${key}/Base/{z}/{y}/{x}.png`, 다크 시 `midnight`) — `data-theme` MutationObserver로 스타일 전환. geojson fill 레이어의 `fill-color`는 rows 조인 후 `metricColor` 매핑, click 시 `onSelectRegion`. `page.tsx`에서 URL 파라미터를 읽어 MapView에 전달.
- [ ] **Step 4: 통과 확인** — `npm test` PASS + dev 서버에서 지도·색칠·클릭 동작 확인 (VWORLD 키를 `frontend/.env.local`에 기입)
- [ ] **Step 5: 커밋** — `"feat(frontend): 지도 탭 — 브이월드 타일 + 단계구분도"`

---

### Task 6: URL 상태 + 업종/지표/연도 토글

**Files:**
- Create: `frontend/src/features/map-explorer/lib/map-state.ts`, `frontend/src/features/map-explorer/components/control-bar.tsx`
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/src/features/map-explorer/lib/map-state.test.ts`

**Interfaces:**
- Produces:
  - `parseMapState(sp: URLSearchParams): MapState` / `serializeMapState(s: MapState): string`
  - `MapState = { industry: string; metric: MetricKey; year: number; region: string | null }` (기본: cafe / closure_rate / 2026 / null)
  - `<ControlBar state onChange>` — 업종 10종·지표 3종·연도 셀렉트 (업종 목록은 상수 `INDUSTRIES` — 백엔드 industry 시드와 동일 id)

- [ ] **Step 1: 실패하는 라운드트립 테스트**

```ts
import { expect, it } from "vitest";
import { parseMapState, serializeMapState } from "./map-state";

it("기본값: 파라미터 없으면 cafe/closure_rate/2026/null", () => {
  expect(parseMapState(new URLSearchParams())).toEqual(
    { industry: "cafe", metric: "closure_rate", year: 2026, region: null });
});
it("직렬화→파싱 라운드트립이 보존된다", () => {
  const s = { industry: "karaoke", metric: "growth_rate" as const, year: 2021, region: "1168051500" };
  expect(parseMapState(new URLSearchParams(serializeMapState(s)))).toEqual(s);
});
it("알 수 없는 값은 기본값으로 강제된다", () => {
  expect(parseMapState(new URLSearchParams("industry=hack&metric=x")).industry).toBe("cafe");
});
```

- [ ] **Step 2: 실패 확인** — `npm test` FAIL
- [ ] **Step 3: 구현** — 화이트리스트 검증 파서 + `useSearchParams`/`router.replace` 연동, ControlBar는 토큰 기반 세그먼트 컨트롤
- [ ] **Step 4: 통과 확인** — `npm test` PASS + dev에서 토글→URL 변경→새로고침 복원 확인
- [ ] **Step 5: 커밋** — `"feat(frontend): URL 상태 + 업종/지표/연도 컨트롤"`

---

### Task 7: 사이드패널 지표 카드 + 신뢰 배지 + AI 딥링크

**Files:**
- Create: `frontend/src/features/map-explorer/components/side-panel.tsx`, `frontend/src/shared/ui/grade-badge.tsx`
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/src/shared/ui/grade-badge.test.tsx`

**Interfaces:**
- Consumes: `RegionSummary`, `apiGet`, `MapState`
- Produces: `<GradeBadge grade="fact"|"signal">` (fact=solid accent, signal=outline 중립 — 스펙 §3 신뢰 배지), `<SidePanel regionCode industry>` — summary query + 카드 리스트 + `[AI 분석 →](/analysis?region=..&industry=..)` Link

- [ ] **Step 1: 실패하는 배지 테스트**

```tsx
import { render, screen } from "@testing-library/react";
import { GradeBadge } from "./grade-badge";

it("fact는 '확인된 사실', signal은 '참고 신호' 라벨", () => {
  render(<><GradeBadge grade="fact" /><GradeBadge grade="signal" /></>);
  expect(screen.getByText("확인된 사실")).toBeInTheDocument();
  expect(screen.getByText("참고 신호")).toBeInTheDocument();
});
```

- [ ] **Step 2: 실패 확인** → **Step 3: 구현** (배지 스타일은 토큰만 사용) → **Step 4: `npm test` PASS + dev에서 동 클릭→패널 표시→AI 버튼 URL 확인**
- [ ] **Step 5: 커밋** — `"feat(frontend): 사이드패널 + 신뢰 배지 + AI 분석 딥링크"`

---

### Task 8: AI 분석 탭 — SSE 훅 + 진행 패널 + 리포트

**Files:**
- Create: `frontend/src/features/agent-report/lib/agent-events.ts`, `frontend/src/features/agent-report/hooks/use-agent-report.ts`, `frontend/src/features/agent-report/components/progress-panel.tsx`, `frontend/src/features/agent-report/components/report-view.tsx`, `frontend/src/features/agent-report/components/analysis-form.tsx`, `frontend/src/app/analysis/page.tsx`
- Test: `frontend/src/features/agent-report/lib/agent-events.test.ts`

**Interfaces:**
- Consumes: `AgentEvent`, `apiPost`, config.apiBase, `GradeBadge`
- Produces:
  - `initialAgentState(): AgentState` / `applyAgentEvent(state: AgentState, ev: AgentEvent): AgentState` — 순수 리듀서. `AgentState = { agents: Record<"orchestrator"|"market"|"shock"|"funding", {status: "idle"|"running"|"done"|"error"; tools: {tool, summary}[]}>; sections: Record<string, string>; done: boolean; citations: unknown[] }`
  - `useAgentReport()` — `{state, start(params)}`: POST `/analysis` → `EventSource(`${apiBase}/analysis/${id}/events`)` 구독, 이벤트마다 리듀서 적용, `report_done`에서 close
  - `/analysis` 페이지: URL 파라미터 프리필된 폼 → 시작 → 진행 패널(좌) + 리포트(react-markdown, 우)

- [ ] **Step 1: 실패하는 리듀서 테스트**

```ts
import { expect, it } from "vitest";
import { applyAgentEvent, initialAgentState } from "./agent-events";

it("agent_status가 해당 에이전트 상태를 갱신한다", () => {
  const s = applyAgentEvent(initialAgentState(),
    { type: "agent_status", agent: "market", status: "running" });
  expect(s.agents.market.status).toBe("running");
});
it("tool_call은 해당 에이전트 타임라인에 누적된다", () => {
  let s = initialAgentState();
  s = applyAgentEvent(s, { type: "tool_call", agent: "market", tool: "지표조회", summary: "강남 카페 폐업률" });
  s = applyAgentEvent(s, { type: "tool_call", agent: "market", tool: "지표조회", summary: "경쟁밀도" });
  expect(s.agents.market.tools).toHaveLength(2);
});
it("report_delta는 섹션별로 이어붙는다", () => {
  let s = initialAgentState();
  s = applyAgentEvent(s, { type: "report_delta", section: "verdict", markdown: "## 결론\n" });
  s = applyAgentEvent(s, { type: "report_delta", section: "verdict", markdown: "가능" });
  expect(s.sections.verdict).toBe("## 결론\n가능");
});
it("report_done이면 done=true", () => {
  const s = applyAgentEvent(initialAgentState(),
    { type: "report_done", report_id: "r1", citations: [] });
  expect(s.done).toBe(true);
});
```

- [ ] **Step 2: 실패 확인** — `npm test` FAIL
- [ ] **Step 3: 구현** — 리듀서(불변 갱신), 훅(EventSource `addEventListener`를 4개 이벤트 타입에 등록, 언마운트 시 close), 진행 패널(에이전트 4행: 이름·상태 점·도구 타임라인 — 모션은 status 전환 트랜지션), 리포트(sections 순서 고정 렌더 + citations 하단), 폼(region·industry 셀렉트, URL 프리필)
- [ ] **Step 4: 통과 확인** — `npm test` PASS + dev에서 mock SSE로 진행 패널→리포트 흐름 육안 확인
- [ ] **Step 5: 커밋** — `"feat(frontend): AI 분석 탭 — SSE 진행 패널 + 리포트"`

---

### Task 9: 상단 바 + 탭 내비 + E2E·스크린샷 자동화

**Files:**
- Create: `frontend/src/shared/ui/top-bar.tsx`, `frontend/scripts/e2e-journey.sh`, `frontend/scripts/screenshot-matrix.sh`
- Modify: `frontend/src/app/layout.tsx`, `frontend/package.json` (scripts)

**Interfaces:**
- Consumes: `ThemeToggle`
- Produces: `<TopBar />` (로고·탭 링크 2개·테마 토글, 현재 탭 하이라이트), npm scripts: `e2e`, `shots`

- [ ] **Step 1: TopBar 구현 + layout 반영** — dev에서 탭 전환·활성 표시 확인
- [ ] **Step 2: agent-browser 설치** — `npm i -g agent-browser && agent-browser install`
- [ ] **Step 3: E2E 여정 스크립트 작성** (`e2e-journey.sh`): agent-browser로 `/ → 동 폴리곤 클릭 → 사이드패널 확인 → [AI 분석] 클릭 → /analysis 프리필 확인 → 시작 → report_done까지 대기 → 리포트 텍스트 존재 assert`
- [ ] **Step 4: 스크린샷 매트릭스 스크립트** (`screenshot-matrix.sh`): 화면(`/`, `/analysis` 시작 전·진행 중·완료) × 테마 2 × 뷰포트(1440·1024) → `frontend/screenshots/` 저장 (디렉토리는 .gitignore)
- [ ] **Step 5: 실행 확인 후 커밋** — 두 스크립트 정상 종료 확인, `"feat(frontend): 탭 내비 + E2E/스크린샷 자동화"`

---

### Task 10: 디자인 폴리시 패스 + 배포 + 버전 로그

**Files:**
- Modify: 폴리시 대상 컴포넌트 전반, `frontend/src/styles/tokens.css`(강조색 확정), `frontend/docs/frontend_ver_log.md`

- [ ] **Step 1: 강조색·폰트 페어링 확정** — `ui-ux-pro-max` 스킬로 신뢰·데이터 계열 팔레트 후보 2~3개 추출 → 스크린샷 매트릭스로 비교 이미지 생성 → 팀 선택 → tokens.css 갱신 (스펙 열린 항목 1 해소)
- [ ] **Step 2: 폴리시 패스** — `frontend-design`+`taste`+`impeccable` 스킬 적용으로 전 화면 다듬기 (금지 목록 준수 확인 포함), `impeccable-finish-reviewer` 서브에이전트 리뷰 → 지적사항 반영
- [ ] **Step 3: 검증 일괄 실행** — `npm test` 전체 PASS + `npm run build` 성공 + 스크린샷 매트릭스 재생성 → 팀 승인
- [ ] **Step 4: Vercel 배포** — Vercel 프로젝트 연결(root: `frontend/`), env(`NEXT_PUBLIC_API_BASE=/api/mock`, `NEXT_PUBLIC_VWORLD_KEY`) 설정, 데모 도메인 연결 확인. 백엔드 전환 시점엔 `NEXT_PUBLIC_API_BASE`만 교체 (CORS는 백엔드 몫 — 별도 백엔드 태스크)
- [ ] **Step 5: 버전 로그 + 커밋·푸시** — `frontend_ver_log.md`에 v0.2.0 기록(스택 핀 버전 포함), 커밋 후 push

---

### Task 11 (2순위 — Task 10까지 승인 후 여유 시): 점포 마커 클러스터

**Files:**
- Create: `frontend/src/features/map-explorer/components/store-markers.tsx`, mock 라우트 `frontend/src/app/api/mock/stores/route.ts`
- Modify: `frontend/src/features/map-explorer/components/map-view.tsx`

- [ ] **Step 1: mock stores 엔드포인트** — `GET /stores?region={code}&industry={id}` → `[{store_id, name, lat, lng, status_name, open_date}]` (fixtures에 동별 20~40개 좌표 — store 테이블 실데이터에서 추출한 표본으로 작성)
- [ ] **Step 2: MapLibre cluster 소스·레이어 추가** — `cluster: true`, 줌인 시 개별 마커, 클릭 시 팝업(상호·개업일·영업상태)
- [ ] **Step 3: 동 선택 시에만 마커 로드** (전 서울 로드는 금지 — 성능 가드)
- [ ] **Step 4: dev 육안 확인 + 스크린샷 매트릭스 갱신 후 커밋** — `"feat(frontend): 점포 마커 클러스터 (2순위)"`

---

## 백엔드 연동 시 잔여 작업 (이 계획 범위 밖 — 백엔드 로드맵에 위임)

- `GET /regions/geojson`·`/metrics`·`/regions/{code}/summary` 실구현 (region_industry_metric 집계 BC와 함께)
- `POST /analysis` + SSE 번역 레이어 (에이전트 이벤트 → §4 프론트 계약)
- CORS 미들웨어 (데모 도메인 + localhost)
