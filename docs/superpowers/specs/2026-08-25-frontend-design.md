# 프론트엔드 설계 스펙 — Metabole 웹 (지도 탐색 + AI 분석)

> 작성: 2026-08-25 (brainstorming 스킬 architectural 경로 — §1~§5 승인 완료분)
> 전제: `docs/brainstorming.md` §7(지도)·§8(금융), `docs/agent-architecture.md`(멀티에이전트·SSE 원천)
> 결정 원칙: **구현은 AI가 담당하므로 구현량은 제약이 아니다. 설계는 사람의 검증 비용을 최소화하는 방향으로 최적화한다.**

## 0. 확정 사항 요약

| 항목 | 결정 |
|---|---|
| 중심 여정 | **탭 2개 대등** (지도 탐색 / AI 분석) + URL 딥링크로 상호 연결 |
| 개발 체제 | AI(Claude) 주도 구현, 팀은 리뷰·승인 |
| 스택 | Next.js(App Router) + TypeScript + Tailwind/shadcn + MapLibre GL + TanStack Query |
| 테마 | **라이트 기본 + 다크 토글, 양 테마 동급 완성도** (시맨틱 토큰 필수) |
| 에이전트 UX | **에이전트별 진행 패널** (SSE) — 멀티에이전트가 눈에 보이는 발표 핵심 장면 |
| 디자인 레퍼런스 | astryx.atmeta.com (Meta 디자인 시스템 — 중립·미니멀·기능 중심) |
| 배포 | Vercel (metabole.beyondfacade.site) → API: cloudflared 터널 도메인 |
| 디자인 스킬 | frontend-design(방향) / ui-ux-pro-max(팔레트·폰트 DB) / taste·impeccable(품질 기준) / agent-browser(QA) |

## 1. 화면 구조

```
상단 바: Metabole | [지도 탐색] [AI 분석] | 테마 토글
[지도 탐색 /]                          [AI 분석 /analysis]
┌─────────────┬──────────┐          ┌─────────┬──────────────┐
│ MapLibre     │ 사이드패널 │          │ 질문 입력 │ 진행 패널       │
│ 단계구분도    │ 지표 카드  │          │ (동·업종  │ 오케스트레이터   │
│ 업종/지표토글 │ 신뢰 배지  │          │  or 자유) │ ├ 상권 진단     │
│ 연도 셀렉트   │ [AI 분석→]│          │          │ ├ 충격 분석     │
│ 점포 마커(2순위)│         │          │          │ └ 정책자금      │
└─────────────┴──────────┘          │ 종합 리포트 (스트리밍+인용)  │
                                     └─────────┴──────────────┘
```

- 탭 간 컨텍스트 전달은 **URL 쿼리로만**: `/analysis?region=11680&industry=cafe` — 딥링크 = 상태 공유 = 새로고침 안전(발표 리스크 제거).
- 계산기(월세vs매입)는 AI 리포트 내 카드로 임베드 — 별도 화면 없음.
- 시계열 슬라이더는 post-MVP — MVP는 연도 셀렉트.

## 2. 기술 구조 (CLAUDE.md Part V 후보 규약)

```
frontend/src/
├── app/                      # 라우팅 셸만 — 로직 금지
│   ├── page.tsx              # / 지도 탐색
│   └── analysis/page.tsx     # /analysis AI 분석
├── features/                 # 기능 1개 = 폴더 1개 = AI 위임 단위
│   ├── map-explorer/         #   components/ hooks/ api.ts types.ts
│   └── agent-report/
├── shared/
│   ├── api/client.ts         # API 베이스·에러 처리 단일 창구
│   ├── ui/                   # shadcn 파생 공용 컴포넌트
│   └── config.ts             # 환경변수 접근 단일 창구
└── styles/                   # 디자인 토큰 (테마 2벌)
```

**규약 3개 (백엔드 §12 대응):**
1. feature 간 직접 import 금지 — 통신은 URL 상태와 `shared/` 경유만.
2. 서버 상태는 전부 TanStack Query (지표·경계 = query 캐시, 리포트 = SSE 구독 훅). 전역 상태 라이브러리 도입 금지 (YAGNI).
3. API 계약은 `features/*/api.ts`에 TS 타입과 함께 격리 — pydantic 스키마 1:1 수동 미러링.

## 3. 디자인 방향

- **테마**: 라이트 기본 + 다크 토글. 모든 색은 시맨틱 CSS 토큰(`--bg-surface` 등)으로만 — 컴포넌트 hex 하드코딩 금지. 지도 타일도 테마 바인딩(라이트=브이월드 기본, 다크=midnight) — 토글 시 타일 동시 전환이 데모 포인트.
- **컬러**: 중립 그레이 스케일 + **강조색 1색** (ui-ux-pro-max 팔레트 DB에서 신뢰·데이터 계열 선정). 단계구분도 팔레트는 강조색과 분리된 별도 체계 — 폐업률·리스크 = warm 순차, 성장률 = 발산, 양 테마·색약 안전 검증.
- **타이포**: Pretendard + 숫자 tabular-nums. 제목은 짧고 임팩트 있는 문장형.
- **밀도**: 지도 탭 = 중밀도 대시보드(숫자 우선), AI 탭 = 여백 있는 문서형.
- **신뢰 배지**: "확인된 사실"(solid) vs "참고 신호"(outline) — brainstorming §5.3 규칙의 시각 언어. 필수 디자인 요소.
- **모션**: 예산을 진행 패널에 집중(상태 전환·도구 호출 타임라인). 단계구분도 전환은 ~300ms 색 보간, 나머지는 마이크로 수준.
- **안티슬롭 금지 목록**: 보라 그라데이션, Inter/system 기본체, 쿠키커터 카드 그림자 — taste/impeccable/frontend-design 스킬이 구현 시 강제.

## 4. 백엔드 API 계약

**① 지도 탭 (조회):**
```
GET /regions/geojson                                   # 행정동 경계 FeatureCollection (불변·무거움 — 별도 캐시)
GET /metrics?industry={id}&year={y}&metric={enum}      # [{region_code, value}] 단계구분도용
GET /regions/{region_code}/summary?industry={id}       # 사이드패널 카드 (지표 + 신뢰등급 필드)
```
`metric` enum: `closure_rate | growth_rate | store_count | …` — region_industry_metric 집계 테이블과 1:1.

**② AI 분석 탭 (SSE):**
```
POST /analysis  {region_code, industry_id, question?}  → {analysis_id}
GET  /analysis/{id}/events  (SSE)
```
이벤트 스키마 (프론트 전용 계약 — LLM SDK 원시 이벤트 노출 금지):
```
agent_status  {agent: market|shock|funding|orchestrator, status: running|done|error}
tool_call     {agent, tool, summary}
report_delta  {section, markdown}
report_done   {report_id, citations[]}
```
백엔드 에이전트 구현 변경(단일→멀티 전환)에도 이 계약은 불변 — 프론트 무수정 보장.
재접속은 MVP에서 "새로고침 = 재실행"으로 절단.

**③ 공통**: 에러 `{error:{code,message}}` 단일 형식 / CORS는 데모 도메인+localhost만 / 코드젠 없음(수동 미러링).

## 5. 검증 전략과 MVP 절단선

**검증 4층:**
1. 단위(Vitest+RTL): 로직 있는 곳만 — SSE 파싱 훅, 색상 스케일, URL 직렬화. 표시 컴포넌트는 제외.
2. 시각 QA 자동화: **agent-browser 스크린샷 매트릭스** (화면 5 × 테마 2 × 뷰포트 2 = 20장) → 사람은 그리드 승인만. impeccable-finish-reviewer 1차 리뷰.
3. E2E 1개: 지도→동 클릭→AI 분석→리포트 완료 (agent-browser, SSE mock → 실서버 전환).
4. 계약: 백엔드 pytest 응답 스키마 스냅샷.
성능 가드: 경계 GeoJSON topology 단순화(수백 KB 이하) + Lighthouse 1회.

**MVP 절단선:**

| 포함 | 제외 (post-MVP) |
|---|---|
| 탭 2 + URL 딥링크 | 시계열 슬라이더 |
| 단계구분도 + 토글 + 연도 셀렉트 | 뉴스 피드 위젯 |
| 사이드패널 카드 + 신뢰 배지 | 모바일 최적화 (태블릿까지만) |
| 진행 패널(SSE) + 리포트 + 인용 | SSE 이벤트 재생·이력 |
| 계산기 카드 | pydantic→TS 코드젠 |
| 점포 마커 클러스터 (2순위) | 커스텀 테마 |
| 라이트+다크 동급 | |

**구축 순서**: 스캐폴드+토큰 → 지도 탭(mock→실API) → AI 탭(**SSE mock 우선** — 백엔드 에이전트 완성 전 UI 완성, 7~9주차 병렬 진행) → 통합 → 폴리시 패스.

## 열린 항목 (구현 중 결정)

1. 강조색·폰트 페어링 최종안 — ui-ux-pro-max DB에서 후보 2~3개 뽑아 스크린샷으로 팀 선택
2. 경계 GeoJSON 제공 방식 — 백엔드 API vs 정적 파일(프론트 번들) 성능 비교 후 결정
3. `/metrics` 백엔드 라우터는 region_industry_metric 집계 BC 구현과 함께 (백엔드 로드맵 §7)
