# Frontend Version Log

## [v0.11.0] - 2026-09-07

### Added
- `frontend/src/features/map-explorer/components/map-view.tsx` — **지도 위 에러 배너** (컷오버 필수 결함 3a): geojson/metrics fetch 실패 시 `role="alert"` 배너 표시(기존 side-panel/analysis의 에러 표시 관행과 일관, `--danger` 토큰). 실 API가 데이터 미보유 업종·연도에 200 + 빈 배열을 반환하는 경우 `role="status"` "지표 데이터 없음" 안내 배너 표시(빈 지도 + 데이터 없음 명시)
- `frontend/src/features/agent-report/components/progress-panel.test.tsx` — 동일 tool+summary 이벤트 반복 시 React key 중복 경고가 없음을 검증하는 TDD 테스트
- `frontend/src/features/agent-report/hooks/use-agent-report.test.ts` — SSE payload가 JSON이 아닐 때 error 상태 합류·스트림 close 검증, `NEXT_PUBLIC_API_BASE`가 실 API여도 분석 POST·SSE가 `/api/mock` 베이스를 유지함을 검증하는 테스트 2건 추가(`FakeEventSource`에 listener 캡처/emit 기능 추가)
- `frontend/src/features/map-explorer/lib/map-state.test.ts` — `YEARS`가 2019~2026 8개년임을 고정하는 계약 테스트(백엔드 v0.9.0 지표 제공 범위와 일치 — 코로나 충격 시계열 조회 가능. 상수 자체는 v0.4.0부터 이미 8개년이라 코드 변경 없음)

### Changed
- `frontend/.env.local` — `NEXT_PUBLIC_API_BASE=http://localhost:8201` 추가(실 API 컷오버, 미커밋 로컬 설정 — 커밋되는 `config.ts`의 `/api/mock` 폴백은 유지)
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — **AI 분석 탭만 mock 유지**: 분석 시작 POST와 SSE `EventSource`가 `config.apiBase` 대신 명시적 `ANALYSIS_API_BASE = "/api/mock"` 상수를 사용(RAG 분석 백엔드 미구현 — 실 분석 API 전환 시 `config.apiBase`로 복귀, TODO 주석)
- `frontend/src/shared/api/client.ts` — `apiPost`에 선택적 `base` 파라미터 추가(기본값 `config.apiBase`, 기존 호출부 무영향)

### Fixed
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — SSE `JSON.parse` 무가드 수정 (컷오버 필수 결함 3b): 손상된 payload를 try/catch로 잡아 `onerror`와 동일한 에러 경로(에러 메시지 + close + finish)에 합류
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 동일 tool+summary 이벤트 반복 시 React key 중복 경고 수정 (컷오버 필수 결함 3c): `tool:summary` content 기반 key → append-only 리스트에서 안정적인 인덱스 포함 key(`{i}:{tool}`)로 교체

### 실 API 계약 검증 (백엔드 v0.9.0, uvicorn 8201)
- `GET /regions/geojson` 427 MultiPolygon, `GET /metrics` 427행, `GET /regions/{code}/summary` fact 카드 3장(side-panel 정상 렌더), `GET /stores` 역삼1동 카페 705행(클러스터 정상 처리, `status_name: "영업"`) — curl + 브라우저(agent-browser) 실검증
- 데이터 미보유 업종(편의점 등 4종)은 `/metrics`·`/stores` 모두 200 + 빈 배열 → 빈 지도 + "지표 데이터 없음" 배너 + summary 카드 "데이터 없음" 값으로 우아하게 처리됨을 확인
- 백엔드 중단 상태에서 지도 접속 시 `role="alert"` 에러 배너 표시 확인. vitest 39건·`tsc --noEmit` 통과

## [v0.10.1] - 2026-09-07

### Changed
- `frontend/src/features/map-explorer/lib/metric-color.ts` — 단계구분도 색상을 연속 보간에서 **이산 7클래스**로 교체 (인접 동 색 대비 강화)
  - sequential: OrRd 5스톱 보간 → **YlOrRd 7클래스 + 분위수(quantile) 경계** — 각 클래스에 비슷한 수의 동이 배분되어 색 다양성이 최대화됨
  - diverging: RdBu 5스톱 보간(도메인 중점 기준) → **RdBu 7클래스 + 0 중심 대칭** — 성장률 부호가 그대로 색 부호(음수=파랑, 0 부근=중립, 양수=빨강)
  - API: `metricColor(value, domain, scheme)` → `makeMetricColorScale(values, scheme)` (값 분포로부터 색상 함수 생성). `map-view.tsx`의 `domainOf` 제거
- `frontend/src/features/map-explorer/lib/metric-color.test.ts` — 분위수 클래스 배분·클램프·0 중심 대칭·빈 값 폴백 6건으로 재작성 (vitest 35건 통과)

## [v0.10.0] - 2026-09-07

### Added
- `frontend/public/geojson/seoul-regions.geojson` — 서울 행정동 427개 실경계 FeatureCollection (5.2MB). 백엔드 v0.8.0 `GET /regions/geojson` 산출물 스냅샷(좌표 5자리 절삭, `properties={region_code, name}` — name은 DB `region.name` 조인). TownPulse(site.townpulse.www)의 프론트 정적 GeoJSON 패턴 참고

### Changed
- `frontend/src/app/api/mock/fixtures.ts` — `SEOUL_SAMPLE_GEOJSON`(강남권 사각형 8개 mock) → `SEOUL_REGIONS_GEOJSON`(실경계 427개, `readFileSync` 로드)으로 교체. `DONGS`/`rectPolygon` 제거, 지역 목록은 `REGIONS`(features의 properties 파생)로 대체 — `metricRows`가 427개 동 전체를 커버해 코로플레스가 서울 전역에 칠해짐
- `frontend/src/features/map-explorer/api.ts` — `RegionGeoJSON` geometry 타입 `Polygon` → `Polygon | MultiPolygon` 확장 (실경계는 전부 MultiPolygon)
- mock 라우트·테스트의 `SEOUL_SAMPLE_GEOJSON` 참조명 일괄 갱신 (동작 변화 없음, vitest 32건 통과)

## [v0.9.1] - 2026-08-26

### Fixed
- `frontend/src/app/api/mock/fixtures.ts` — `metricRows(metric, year, industry)`에 `industry` 인자 추가, `hashSeed` 입력에 포함해 지표(choropleth)가 업종별로 달라지도록 수정. `summaryOf`가 점포수/폐업률/성장률 카드 계산 시 `metricRows`에 `industry`를 전달하도록 변경 — 업종을 바꿔도 지도 색상·요약 카드 수치가 그대로였던 데모 결함 수정
- `frontend/src/app/api/mock/metrics/route.ts` — `industry` 쿼리 파라미터를 읽어 `metricRows`에 전달, `stores` 라우트와 대칭인 `INDUSTRY_NOT_FOUND` 404 가드 추가
- `frontend/src/features/map-explorer/components/side-panel.tsx` — 에러 상태 div에 `role="alert"` 추가 (`analysis-page.tsx`의 기존 패턴과 일치)
- `frontend/src/app/api/mock/metrics/route.test.ts`, `frontend/src/app/api/mock/fixtures.test.ts` — industry 파라미터 필수화에 맞춰 기존 테스트 업데이트, 업종별 값 분산·결정성(같은 조합→동일 값) 검증 테스트 추가

## [v0.9.0] - 2026-08-26

### Added
- `frontend/src/app/api/mock/store-samples.ts` — backend `store` 테이블 실데이터(297k행, beyondfacade-db)에서 8개 동 × 6개 업종(billiard/cafe/gym/hair_salon/karaoke/pc_bang) bounding box로 필터링해 추출한 점포 표본(`STORE_SAMPLES`, 동×업종당 최대 20건). store 테이블에 실적재 데이터가 없는 업종(convenience_store/real_estate/academy/childcare)은 표본에 없음 — 해당 조합은 의도적으로 빈 배열
- `frontend/src/app/api/mock/stores/route.ts` — `GET /stores?region={code}&industry={id}` mock 라우트. 미등록 region은 404 `REGION_NOT_FOUND`, 미지원 industry는 404 `INDUSTRY_NOT_FOUND`(metrics 라우트의 `METRIC_NOT_FOUND` 가드와 대칭)
- `frontend/src/app/api/mock/stores/route.test.ts` — 정상 조회/미등록 region/미지원 industry/실적재 데이터 없는 업종(빈 배열) TDD 테스트 4건
- `frontend/src/app/api/mock/fixtures.ts` — `storesOf(regionCode, industryId)`: `STORE_SAMPLES`를 region·industry로 필터링해 `Store[]` 반환
- `frontend/src/features/map-explorer/components/store-markers.tsx` — `<StoreMarkers>`: MapLibre GeoJSON 클러스터 소스(`cluster: true`, `clusterMaxZoom: 14`, `clusterRadius: 50`) + 클러스터/클러스터 카운트/비클러스터 3개 레이어. 클러스터 클릭 시 `getClusterExpansionZoom`으로 확대, 개별 마커 클릭 시 상호·개업일·영업상태 팝업. 동 선택(`regionCode`) 없으면 소스를 빈 FeatureCollection으로 유지(성능 가드 — 전 서울 로드 금지). 클러스터/마커 페인트 색상은 `map-view.tsx`와 동일한 `--accent`/`--bg-surface`/`--accent-fg` 토큰을 읽어 적용하고, `data-theme` `MutationObserver`로 테마 전환 시 재적용
- `frontend/src/features/map-explorer/api.ts` — `fetchStores(regionCode, industry)` 추가 (`apiGet` 경유)
- `frontend/src/shared/api/types.ts` — `Store` 인터페이스(`store_id, name, lat, lng, status_name, open_date`)

### Changed
- `frontend/src/features/map-explorer/components/map-view.tsx` — `readAccentColor()`를 export(마커 페인트 색상도 동일 토큰을 읽어야 하므로), `<StoreMarkers>`를 지도 컨테이너에 배선(`mapRef`/`ready`/`regionCode`/`industry` 전달)
- `frontend/scripts/e2e-journey.sh` — 사이드패널 확인 직후 "점포 마커 로드 확인" 단계 추가(동 선택 후 `GET /api/mock/stores` 네트워크 요청 발생 여부를 `agent-browser network requests --filter`로 검증 — WebGL 캔버스 클러스터는 DOM으로 직접 검사할 수 없어 그 트리거인 네트워크 요청으로 배선을 확인). 단계 번호 7→8단계로 재조정
- `frontend/scripts/screenshot-matrix.sh` — 동 선택 후 점포 마커/클러스터가 보이는 지도 화면(`map-markers_{theme}_{width}.png`) 스크린샷 추가

## [v0.8.0] - 2026-08-26

### Added
- `frontend/src/shared/industries.ts` — 업종 id 목록(`INDUSTRIES`)과 한국어 라벨(`INDUSTRY_LABELS`, `industryLabel()`)의 공통 어휘 모듈. 지도 탐색·AI 분석 두 feature가 함께 쓰므로 feature 간 직접 import 금지 규칙에 따라 `shared/`에 배치 (`map-state.ts`의 `INDUSTRIES` 정의를 이곳으로 이동)
- `frontend/src/shared/ui/route-fallback.tsx` — 라우트 셸 `<Suspense>` 폴백 컴포넌트 (`role="status"`, 레이아웃 높이 유지)
- `frontend/src/app/api/mock/metrics/route.test.ts` — metrics mock 라우트 TDD 테스트 2건 (지원 metric 200 / 미지원 metric 404 `METRIC_NOT_FOUND`)
- `frontend/src/app/globals.css` — `.report-markdown` 스코프 스타일. Tailwind preflight가 리셋한 리포트 마크다운 요소(h2/h3, p, strong, ul/ol, table/th/td)를 토큰 기반으로 복원하고 표에 `tabular-nums` 적용. `prefers-reduced-motion` 감축 규칙 추가
- `frontend/src/features/map-explorer/lib/map-state.ts` — `METRIC_LABELS` (폐업률·성장률·점포수)

### Changed
- `frontend/src/styles/tokens.css` — **강조색 확정 (스펙 열린 항목 1 해소)**: `ui-ux-pro-max` 팔레트 DB의 신뢰·데이터 계열 후보 3종(civic-navy / market-teal / ink-sky)을 스크린샷으로 비교해 **market-teal** 선택 — 라이트 `--accent: #0f766e` / 다크 `--accent: #2dd4bf`. 중립 스케일·`--ok/--warn/--danger`를 포함한 라이트/다크 11종 토큰 세트 전체를 확정값으로 교체. 선정 근거: 단계구분도 팔레트(warm 순차 / 청·적 발산)와 색상환이 겹치지 않아 지도 위 선택 강조선이 데이터색과 혼동되지 않으며, 상권·부동산 도메인 정합이 가장 높음
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 지표 세그먼트가 raw id(`closure_rate` 등) 대신 한국어 라벨을 표시(값·URL 파라미터는 영문 유지), 업종 select도 한국어 라벨 표시. 각 컨트롤에 보이는 라벨(업종/지표/연도) 추가, 세그먼트에 `role="group"`+`aria-pressed`, 전 컨트롤에 `focus-visible` 아웃라인·hover·`active` 피드백 부여
- `frontend/src/features/map-explorer/components/side-panel.tsx` — 미선택/에러 상태를 안내 문구가 있는 구성된 빈 상태로 교체, 로딩을 텍스트 대신 스켈레톤으로 교체(`role="status"`), 지표 목록을 카드 대신 `divide-y` 구분선 구성으로 변경, 헤더에 region_code·업종 라벨 캡션 추가, CTA 버튼에 hover/active/focus 상태 추가
- `frontend/src/features/agent-report/components/analysis-form.tsx` — 지역 코드·업종을 2열 그리드로 배치하고 폼 너비를 `max-w-xl`로 제한(1440px에서 입력창이 전폭으로 늘어나던 문제), 업종 입력 아래 한국어 라벨 힌트 표시(입력값 자체는 API 계약상의 영문 id 유지), 추가 질문 placeholder, 제출 버튼 로딩 라벨("분석 중…")·focus/active 상태
- `frontend/src/features/agent-report/components/analysis-page.tsx` — 컨테이너 `max-w-[1400px]` 중앙 정렬, 진행 패널/리포트를 `lg` 이상에서만 2열로 분기(그 이하는 세로 스택), 에러 메시지에 `role="alert"`
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 에이전트 4행을 카드 4개 대신 `divide-y` 타임라인으로 변경, `role="status" aria-live="polite"` 부여, 상태를 색상 점만이 아니라 텍스트 라벨(대기/진행 중/완료/오류)로도 노출(색상 단독 전달 금지 규칙)
- `frontend/src/features/agent-report/components/report-view.tsx` — 섹션에 `.report-markdown` 클래스 적용(제목·표·목록 스타일 복원), 빈 상태를 구성된 안내 박스로 교체, 참고 자료 목록을 `divide-y`+underline-offset 링크로 정리
- `frontend/src/shared/ui/top-bar.tsx` — 활성 탭을 색상만이 아니라 하단 2px 인디케이터로도 표시, 탭에 hover/focus-visible 상태, 헤더 `shrink-0`
- `frontend/src/shared/ui/theme-toggle.tsx`, `frontend/src/shared/ui/grade-badge.tsx` — hover/focus-visible/active 상태, 배지 `shrink-0 whitespace-nowrap`(좁은 패널에서 줄바꿈 방지)
- `frontend/src/app/page.tsx`, `frontend/src/app/analysis/page.tsx` — `<Suspense>`에 `<RouteFallback>` 지정(기존에는 fallback 없음)
- `frontend/package.json`, `frontend/scripts/e2e-journey.sh`, `frontend/scripts/screenshot-matrix.sh` — **포트 규약 정정 3500 → 3200** (`next dev/start -p 3200`, 스크립트 `BASE_URL` 기본값 및 헤더 주석). 루트 `docker-compose.yml`의 frontend 서비스 포트(3200)와 일치
- `frontend/scripts/e2e-journey.sh` — 역삼1동 폴리곤 클릭 좌표를 하드코딩(666,538) 대신 런타임 계산으로 변경. 지도 컨테이너의 실제 `getBoundingClientRect()`에 웹 메르카토르 투영(zoom 11, bearing/pitch 0)으로 구한 오프셋을 더한다. 상단바·컨트롤바 높이가 바뀌면 하드코딩 좌표가 조용히 빗나가던 취약성 제거(이번 레이아웃 변경으로 실제 좌표가 538 → 700으로 이동)

### Fixed
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 존재하지 않는 토큰 `--border-color`를 참조해 border 선언이 무효화되고 `currentColor`로 폴백되던 버그 수정 (올바른 토큰명은 `--border`)
- `frontend/src/app/layout.tsx`, `frontend/src/features/map-explorer/components/map-page.tsx`, `map-view.tsx` — `/` 지도 화면이 뷰포트 높이를 채우지 못하고 하단에 빈 영역이 남던 레이아웃 버그 수정. `<body>`의 `min-h-full`은 `<html>`에 높이가 없어 해석되지 않으므로 `min-h-[100dvh]`로 교체하고, flex 체인에 `min-h-0`·`overflow-hidden`을 추가해 `MapView`의 `h-full`이 실제로 남은 높이를 받도록 함(`min-h-[480px]` → `min-h-[320px]` 안전 하한)
- `frontend/src/app/api/mock/metrics/route.ts` — 미지원 `metric` 파라미터가 들어오면 `METRIC_RANGES` 조회 실패로 500이 나던 문제 수정. summary 라우트의 `REGION_NOT_FOUND` 가드와 대칭으로 404 `METRIC_NOT_FOUND`를 반환하도록 검증 추가
- `frontend/src/app/layout.tsx` — `<title>`이 스캐폴드 기본값("Create Next App")으로 남아 있던 문제 수정 → "Metabole — 상권 분석" + 설명 metadata

### 스택 핀 버전
`next@16.3.2` / `react@19.2.8` · `react-dom@19.2.8` / `maplibre-gl@^6.6.0` / `@tanstack/react-query@^5.102.3` / `react-markdown@^10.1.0` · `remark-gfm@^4.0.1` / `tailwindcss@^4` · `@tailwindcss/postcss@^4` / `typescript@^5` / `vitest@^4.1.11` · `jsdom@^29.1.1` · `@testing-library/react@^16.3.2`

## [v0.7.2] - 2026-08-26

### Fixed
- `frontend/src/features/map-explorer/components/map-view.tsx` — 지도 탭에서 행정동 폴리곤(단계구분도)이 전혀 렌더/클릭되지 않던 버그 수정. 근본 원인: maplibre-gl@6.6.0은 GeoJSON 타일링을 수행하는 워커 스크립트의 URL을 `import.meta.url` 기반으로 런타임에 자체 계산하는데, Turbopack 번들 청크의 `import.meta.url`은 http(s) URL이 아니어서 그 계산이 빈 문자열로 실패해 워커가 뜨지 못하고 타일링이 조용히 멈춰 있었다(콘솔/네트워크 에러 없음). `maplibre-gl`의 `setWorkerUrl()`로 워커 스크립트 경로를 명시 지정해 우회. Turbopack의 `new URL(path, import.meta.url)` 정적 에셋 처리는 참조 파일을 해시된 이름으로 그대로 복사할 뿐 내부 상대 import(`./maplibre-gl-shared.mjs`)는 재작성하지 않으므로, `maplibre-gl-worker.mjs`와 `maplibre-gl-shared.mjs`를 원본 파일명 그대로 `frontend/public/maplibre-gl/`에 함께 두고 그 경로를 지정했다(버전 `maplibre-gl@6.6.0` 고정, 이 패키지를 업그레이드하면 두 파일도 함께 갱신해야 함).
- `frontend/scripts/e2e-journey.sh` — 위 렌더링 버그가 고쳐지면서 실제로 폴리곤을 클릭해 보니, 기존 클릭 좌표(613, 446)가 `map.project()`의 지도-컨테이너 상대 좌표를 그대로 페이지 절대 좌표로 오인해 계산된 값이라 실제로는 대상 폴리곤을 빗나가고 있었음을 확인. 지도 컨테이너의 페이지 오프셋(top:114, left:0)을 더한 올바른 페이지 절대 좌표(666, 538)로 교정.
- `frontend/package.json` — `e2e` 스크립트에서 `E2E_XFAIL_CLICK=1` 기본값 제거. 지도 렌더링 버그가 해결되어 `npm run e2e`가 실제 폴리곤 클릭 경로까지 엄격 모드(클릭 실패 시 exit 1)로 통과한다.

## [v0.7.1] - 2026-08-26

### Fixed
- `frontend/scripts/e2e-journey.sh` — "동 폴리곤 클릭" 단계가 실패해도 stderr 경고만 남기고 조용히 폴백 내비게이션 후 exit 0으로 통과하던 문제 수정: 기본 동작은 클릭 실패 시 exit 1(명확한 한국어 오류 메시지)로 종료하도록 변경. 알려진 지도 렌더링 버그로 인한 실패를 의도적으로 우회하려면 `E2E_XFAIL_CLICK=1`을 명시적으로 지정해야 하며, 이 경우 최종 stdout 요약에 `XFAIL: 폴리곤 클릭 (지도 렌더링 버그)` 줄이 출력된다. 스크립트 헤더 주석에 두 모드를 문서화.
- `frontend/scripts/e2e-journey.sh`, `frontend/scripts/screenshot-matrix.sh` — `set -euo pipefail` 하에서 중간 단계가 실패하면 스크립트 마지막의 `AB close`가 실행되지 못해 헤드리스 브라우저/agent-browser 데몬 프로세스가 누수되던 문제 수정: 스크립트 상단에 `trap 'AB close >/dev/null 2>&1 || true' EXIT`를 추가해 정상/비정상 종료 모두에서 정리되도록 함(기존 말미의 중복 `AB close` 호출 제거).
- `frontend/package.json` — `e2e` npm 스크립트를 `E2E_XFAIL_CLICK=1 bash scripts/e2e-journey.sh`로 변경해, 지도 렌더링 버그가 열려 있는 동안 기본 `npm run e2e`는 계속 녹색을 유지하도록 함. 원본 스크립트(`bash scripts/e2e-journey.sh`)는 계속 엄격 모드를 유지하며, 지도 버그 수정 후 이 환경변수 없이 재검증해야 함.

## [v0.7.0] - 2026-08-26

### Added
- `frontend/src/shared/ui/top-bar.tsx` — `<TopBar />`: 로고("Metabole") + 탭 링크 2개(`/` 지도 탐색, `/analysis` AI 분석, `usePathname` 기반 `aria-current`/accent 하이라이트) + `<ThemeToggle />` 배치
- `frontend/src/shared/ui/top-bar.test.tsx` — 현재 경로 탭에 `aria-current="page"`가 붙는지 검증하는 TDD 테스트
- `frontend/scripts/e2e-journey.sh` — agent-browser(`npx -y agent-browser`) 기반 E2E 여정: `/` → 동 폴리곤 클릭 → 사이드패널 확인 → `[AI 분석 →]` 클릭 → `/analysis` 프리필 확인 → 분석 시작 → `report_done`까지 대기 → 리포트 텍스트 존재 assert. dev 서버 미기동 시 한국어 오류 메시지로 종료
- `frontend/scripts/screenshot-matrix.sh` — 화면(`/`, `/analysis` 시작 전·진행 중·완료) × 테마(light/dark, `ThemeToggle` 클릭으로 전환) × 뷰포트(1440/1024) 16종 스크린샷을 `frontend/screenshots/`에 저장
- `package.json` scripts: `e2e`, `shots`

### Changed
- `frontend/src/app/layout.tsx` — `<body>` 내부 `{children}` 위에 `<TopBar />` 렌더
- `frontend/.gitignore` — `/screenshots/` 추가 (E2E/스크린샷 산출물은 커밋 대상 아님)
- `package.json` — `dev`/`start` 스크립트 포트를 3000 → 3500으로 변경 (`next dev -p 3500`, `next start -p 3500`)

## [v0.6.1] - 2026-08-25

### Fixed
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — `start()` 재진입 가드 없음으로 인한 `EventSource` 누수 수정: `loadingRef`로 `apiPost` await 이전에 동기적으로 재진입을 차단(진행 중이면 무시), `loading` 상태를 훅 반환값에 추가. `apiPost` 실패를 `try/catch`로 잡아 `state.error`에 반영(기존에는 unhandled rejection이었음)
- `frontend/src/features/agent-report/components/analysis-page.tsx` — `useAgentReport().loading`을 `AnalysisForm`의 `disabled`로 실제 전달(더블클릭 방지 UI 배선)
- `frontend/src/features/agent-report/components/progress-panel.tsx`, `report-view.tsx` — 타임라인/인용 리스트의 index key를 `tool:summary`/`title:url` 조합 키로 교체

### Added
- `frontend/src/features/agent-report/hooks/use-agent-report.test.ts` — `EventSource`/`fetch` mock으로 `start()` 연속 호출 시 연결이 1개만 생성됨을 검증하는 재진입 가드 테스트

## [v0.6.0] - 2026-08-25

### Added
- `frontend/src/features/agent-report/lib/agent-events.ts` — `initialAgentState()`/`applyAgentEvent(state, ev)` 순수 리듀서. `AgentState = { agents: Record<AgentName, {status, tools}>; sections: Record<string, string>; done; citations; error }`, 4개 `AgentEvent` 타입별 불변 갱신
- `frontend/src/features/agent-report/lib/agent-events.test.ts` — agent_status/tool_call 누적/report_delta 이어붙임/report_done TDD 테스트 4건
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — `useAgentReport()`: `apiPost("/analysis", ...)` → `EventSource(\`${config.apiBase}/analysis/{id}/events\`)` 구독, 4개 이벤트 타입 `addEventListener` → 리듀서 적용, `report_done`/언마운트 시 close, `onerror` 시 `error` 상태 노출
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 에이전트 4행(오케스트레이터/상권 진단/충격 분석/정책자금) 상태 점(idle/running/done/error, 토큰 기반) + 도구 호출 타임라인(최근 항목 강조)
- `frontend/src/features/agent-report/components/report-view.tsx` — 섹션 순서 고정(`verdict,market,shock,funding,calculator`) `react-markdown`(+`remark-gfm`) 렌더, `report_done` 시 citations 목록(`GradeBadge`) — unknown 배열 런타임 가드
- `frontend/src/features/agent-report/components/analysis-form.tsx` — 지역 코드/업종/자유 질문 입력 폼, URL 프리필
- `frontend/src/features/agent-report/components/analysis-page.tsx` — map-page 패턴의 클라이언트 컴포넌트: URL region·industry 프리필 → 폼 → 진행 패널(좌) + 리포트(우)
- `frontend/src/app/analysis/page.tsx` — 서버 컴포넌트 + `<Suspense>`로 `AnalysisPage` 감싸기
- `remark-gfm` 의존성 (계산기 섹션 마크다운 표 렌더)

## [v0.5.0] - 2026-08-25

### Added
- `frontend/src/shared/ui/grade-badge.tsx` — `<GradeBadge grade="fact"|"signal">` 신뢰 배지 (fact=accent solid, signal=outline 중립, 토큰 기반)
- `frontend/src/shared/ui/grade-badge.test.tsx` — fact/signal 라벨 렌더 TDD 테스트
- `frontend/src/features/map-explorer/components/side-panel.tsx` — `<SidePanel regionCode industry>`: region summary TanStack Query(`enabled: !!regionCode`), 미선택/로딩/404("데이터 없음") 상태 분기, 카드 리스트 + `[AI 분석 →]` `/analysis?region=..&industry=..` 딥링크
- `frontend/src/features/map-explorer/api.ts` — `fetchRegionSummary(regionCode, industry)` 추가 (`apiGet` 경유)

### Changed
- `frontend/src/features/map-explorer/components/map-page.tsx` — `SidePanel`을 `MapView` 우측에 배선 (지도 flex-1 래퍼로 폭 조정)

## [v0.4.0] - 2026-08-25

### Added
- `frontend/src/features/map-explorer/lib/map-state.ts` — `MapState` 인터페이스, `parseMapState`/`serializeMapState` 라운드트립, `INDUSTRIES`/`METRICS`/`YEARS` 화이트리스트 상수
- `frontend/src/features/map-explorer/lib/map-state.test.ts` — 기본값/라운드트립/유효성 검증 TDD 테스트 3건
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 업종 select/지표 segment/연도 select 컨트롤 (색상 토큰 기반)

### Changed
- `frontend/src/features/map-explorer/components/map-page.tsx` — `useRouter`/`useSearchParams` 통합: URL ↔ state 양방향 동기화, `ControlBar` 렌더, region 선택 → URL 반영
- `frontend/src/app/page.tsx` — `<Suspense>` 경계 추가 (useSearchParams 클라이언트 컴포넌트 감싸기)

## [v0.3.1] - 2026-08-25

### Fixed
- `map-view.tsx` — 테마(`data-theme`) 전환 시 선택 강조 line-color가 이전 테마의 `--accent`로 남던 버그. 테마 `MutationObserver` 콜백에서도 `readAccentColor()`로 line-color를 재적용하도록 수정.
- `map-view.tsx` — `#cccccc`/`#000000` 하드코딩 hex를 lib 상수/토큰 참조로 교체: `NO_DATA_COLOR`를 `metric-color.ts`에서 export해 fill-color 폴백 2곳에 재사용, 초기 line-color는 리터럴 대신 `readAccentColor()`로 시드.

## [v0.3.0] - 2026-08-25

### Added
- `frontend/src/features/map-explorer/lib/metric-color.ts` — sequential/diverging 색약 안전 5스톱 RGB 선형 보간 + 클램프 (`metricColor`)
- `frontend/src/features/map-explorer/lib/metric-color.test.ts` — 도메인 클램프/단조 증가/중립색 검증
- `frontend/src/features/map-explorer/api.ts` — `fetchRegionsGeoJson`, `fetchMetrics` (`apiGet` 경유)
- `frontend/src/features/map-explorer/hooks/use-map-data.ts` — `useMapData(metric, industry, year)`: geojson(staleTime Infinity) + metrics rows TanStack Query
- `frontend/src/features/map-explorer/components/map-view.tsx` — MapLibre 지도(서울 중심, zoom 11), 브이월드 라이트/다크 래스터 타일(`data-theme` MutationObserver로 전환), geojson 단계구분도(fill match expression) + 선택 강조(line 레이어) + 클릭 시 `onSelectRegion`
- `frontend/src/features/map-explorer/components/map-page.tsx` — 클라이언트 상태 보관용 얇은 래퍼 (`page.tsx` 서버 컴포넌트 유지를 위한 경계)

### Changed
- `frontend/src/app/page.tsx` — Next 기본 스캐폴드 마크업 제거, `MapPage` 렌더로 교체

## [v0.2.0] - 2026-08-25

### Added
- Next.js 16 앱 스캐폴드 (`create-next-app`: TypeScript, App Router, Tailwind, `src/` 디렉토리, `@/*` import alias)
- `@tanstack/react-query`, `maplibre-gl`, `react-markdown` 의존성
- Vitest 테스트 러너 (`frontend/vitest.config.ts`, `frontend/src/test/setup.ts`) + `@testing-library/*`, `jsdom`
- `frontend/src/shared/config.ts` — `NEXT_PUBLIC_API_BASE` 기반 `config.apiBase` (기본값 `/api/mock`), `config.vworldKey`
- `frontend/src/shared/config.test.ts` — `config.apiBase` 기본값 검증
- `package.json` scripts: `test`, `test:watch`

## [v0.1.0] - 2026-08-24

### Added
- `frontend/Dockerfile` — node:22-alpine 로컬 개발용 이미지 (배포는 Vercel 담당, 스택 확정 후 동작)
- 루트 docker-compose.yml에 `frontend` 프로필 서비스 등록 (포트 3200, 스택 확정 전 기본 기동 제외)
