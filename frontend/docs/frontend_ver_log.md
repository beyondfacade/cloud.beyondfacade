# Frontend Version Log

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
