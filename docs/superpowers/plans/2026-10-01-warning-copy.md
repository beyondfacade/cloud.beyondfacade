# 플랜 — 창업 경고 문구 정비 (스펙: `docs/superpowers/specs/2026-10-01-warning-copy-design.md`)

> 스펙이 구속력 있는 명세다. 각 Task는 스펙의 해당 절을 **읽고** 구현한다. 바꿀 문구의 정확한 글자는 스펙 §4 표의 "바꿀 문구" 열이 정본이다.

> 원 작업(v0.52.0)의 실행 계획이다. 독립 리뷰 후속 수정과 지원 복귀 링크 변경은 [`2026-10-01-warning-copy-review-fixes.md`](2026-10-01-warning-copy-review-fixes.md)를 따른다. 아래 예외·문구 참조는 최종 설계서에 맞춰 정정했다.

## Global Constraints

- 저장소 루트 `CLAUDE.md`를 따른다: TDD(Red → Green), 최소 변경, 주변 코드·서식·주석을 "개선"하지 않는다, 기존 스타일 유지.
- `frontend/AGENTS.md`: 이 Next.js는 학습 데이터와 다를 수 있다 — 문구 외의 API·구조는 건드리지 않는다.
- **문구 교체만** 한다. 마크업 구조·className·href·레이아웃은 그대로 둔다. 예외는 스펙 §3의 네 가지뿐(랜딩 보조 링크 앵커 `#about`, 지도 범례 한 줄 추가, `.about h2`의 `word-break: keep-all`, 소개 02의 강제 줄바꿈 제거).
- 줄바꿈 `<br />`·강조 `<span>` 위치는 소개 02 예외 외에는 기존 마크업을 따른다. 스펙 표의 `/`는 줄바꿈 자리, `·`로 나뉜 항목은 (번호 라벨 · 제목 · 본문) 또는 (제목 · 작은 글씨) 순서다.
- 색은 토큰만 쓴다(`text-[var(--...)]`). 새 hex 금지. feature 간 직접 import 금지.
- 스펙 §3 "범위 밖"과 §4-2·§4-4의 "그대로 둔다" 항목은 건드리지 않는다(파서 테스트 입력 "연남동에서 뭘 하면 좋을까", "해당 가능성이 있는 공고" 등).
- 테스트 제목은 한국어 서술문, 테스트 파일은 대상 파일 옆 co-located.
- 테스트 명령: `cd frontend && npx vitest run && npx tsc --noEmit`. 백엔드는 건드리지 않는다.
- 버전 로그: `frontend/docs/frontend_ver_log.md`의 **`[v0.52.0] - 2026-10-01`** 한 항목에 Task 1·2가 누적한다(Task 1이 항목을 만들고 Task 2가 덧붙인다). 형식은 파일의 기존 항목을 따른다.
- 커밋: 자기 Task가 고친 파일만 `git add <경로>`로 스테이징해 `feat/warning-copy` 브랜치에 커밋한다. 메시지는 기존 관례 `frontend v0.52.0: <한 줄>`. push 하지 않는다.

### Task 1: 랜딩·메타·관문·상단 메뉴·로그인 문구 (스펙 §4-1 · §4-2 · §4-5 일부)

파일:
- `frontend/src/features/landing/components/landing-page.tsx` — 스펙 §4-1 표 전부. 보조 링크 href를 `#how-it-works` → `#about`.
- `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx` — 메타 title·description(§4-1 표 마지막 세 줄).
- `frontend/src/features/intent-gate/components/intent-form.tsx` — 버튼 "확인하기"(대기 중 "확인 중…"), `EXAMPLE_CHIPS` 두 번째를 "망원동에 한식집"으로.
- `frontend/src/features/intent-gate/components/diagnosis-line.tsx` — "지도에서 확인" → "근거 보기".
- `frontend/src/shared/ui/top-bar.tsx` — 메뉴 라벨 "경고 지도"·"리포트".
- `frontend/src/features/auth/components/auth-layout.tsx` — 로그인 안내 문장.
- `frontend/scripts/e2e-journey.sh` — 관문 렌더 대기는 `AB wait --text "어느 동네에서 무엇을 하려고 하세요?"`, 로그·주석의 "지도 탐색"·"AI 분석"을 새 메뉴 이름으로.
- `frontend/docs/frontend_ver_log.md` — `[v0.52.0] - 2026-10-01` 항목 생성.

테스트(먼저 Red):
- `frontend/src/app/page.test.tsx` — 주 버튼 이름 "창업 경고 지도 보기"(테스트 제목의 "탐색 시작 링크"도 맞게 고친다). 추가: 랜딩 h1이 "가게 자리를 찾기 전에, 피해야 할 자리부터 확인하세요."로 읽히고, 화면 어디에도 "가능성"이 없다. 추가: 보조 링크 "어떻게 판정하나요?"가 `#about`을 가리킨다.
- `frontend/src/shared/ui/top-bar.test.tsx` — 메뉴 이름과 테스트 제목.
- `frontend/src/features/intent-gate/components/intent-gate.test.tsx` — `submit` 헬퍼의 버튼 정규식을 `/확인하기|확인 중/`으로. 진단 뒤 링크 이름을 단언하는 테스트가 있으면 "근거 보기"로.

완료 기준: 위 테스트가 Red였다가 Green, `npx vitest run` 전부 통과, `npx tsc --noEmit` 통과. `grep -rnE '자리를 찾다|상권 탐색하기|어떻게 시작하나요|지도 열기|찾아보기|지도에서 확인|지도 탐색|새로운 시선|YOUR NEXT CHAPTER|A NEW PERSPECTIVE' frontend/src --include=*.tsx --include=*.ts | grep -v '/admin/'` 결과에서 주석(`shared/industries.ts`·`shared/neighborhood.ts`의 "지도 탐색" 주석)만 남는다.

### Task 2: 지도·AI 분석·자금 계획 문구 + 범례 안내 줄 (스펙 §4-3 · §4-4 · §4-5 일부)

파일:
- `frontend/src/features/map-explorer/components/control-bar.tsx`, `map-page.tsx`, `side-panel.tsx` — 스펙 §4-3 표.
- `frontend/src/features/map-explorer/components/map-legend.tsx` — 범례에 `"경고 없음"은 추천이 아닙니다.` 한 줄 추가(기존 범례 글자 스타일·토큰을 따른다).
- `frontend/src/features/agent-report/components/analysis-page.tsx`, `report-view.tsx` — 스펙 §4-4 표. `report-view.tsx`는 "NEIGHBORHOOD REPORT" 2곳, 리포트 이름, `aria-label` 모두.
- `frontend/src/features/plan/components/plan-page.tsx` — "← 경고 지도로".
- `frontend/scripts/e2e-journey.sh` — `[aria-label="상권 분석 리포트"]` → `[aria-label="창업 경고 리포트"]`.
- `frontend/docs/frontend_ver_log.md` — Task 1이 만든 `[v0.52.0]` 항목에 덧붙인다(Changed + Added: 범례 안내 줄).

테스트(먼저 Red):
- `frontend/src/features/map-explorer/components/side-panel.test.tsx` — 빈 화면 제목 "어느 동네를 보고 계세요?".
- `frontend/src/features/map-explorer/components/map-legend.test.tsx` — 추가: 범례에 `"경고 없음"은 추천이 아닙니다.`가 보인다.
- `frontend/src/features/map-explorer/components/map-page.test.tsx` — 추가(또는 기존 단언 수정): h1 "피해야 할 동네부터 보입니다.".
- `frontend/src/features/agent-report/components/` — `report-view`·`analysis-page` 테스트 파일이 있으면 거기에 추가: 리포트 article의 접근성 이름이 "창업 경고 리포트", 분석 화면 h1이 "판정의 근거를, 한 장으로."로 읽힌다. 옛 문구를 단언하는 기존 테스트는 새 문구로 고친다.

완료 기준: 위 테스트가 Red였다가 Green, `npx vitest run` 전부 통과, `npx tsc --noEmit` 통과. `grep -rnE '어떤 상권이 궁금|어느 동네가 궁금|지표와 신호가|지표 확인|한 장의 분석|다음 단서|또 하나의 시선|상권 분석 리포트|상권 탐색으로|NEIGHBORHOOD REPORT|YOUR PERSPECTIVE|동네의 가능성|다음 가능성' frontend/src frontend/scripts | grep -v '/admin/'` 결과가 비어 있다.
