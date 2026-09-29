# 플랜 — 화면 재편 (스펙: `docs/superpowers/specs/2026-09-29-screen-restructure-design.md`)

> 스펙이 구속력 있는 명세다. 각 Task는 스펙의 해당 절을 **읽고** 구현한다. 아래 Task 본문은 범위·파일·완료 기준만 적는다.

## Global Constraints

- CLAUDE.md(`docs/CLAUDE.md`, 프론트는 `frontend/docs/CLAUDE.md`)를 따른다: TDD(Red→Green), 최소 변경, 내 변경이 만든 미사용 코드는 삭제, 기존 패턴 유지.
- 계약 표(스펙 §6)를 프론트·백엔드가 각자 지킨다 — 섹션 키 `verdict, reasons, conditions, alternatives, funding`, 스테이지 `orchestrator, verdict, market, shock, funding`, 도구 `get_verdict`·`get_verdict_alternatives`, `POST /analysis {region, industry, question?, model?, budget?}`.
- 버전 로그: BE `backend/docs/backend_ver_log.md` **v0.44.0** 한 항목에 T1·T2가 누적, FE `frontend/docs/frontend_ver_log.md` **v0.31.0** 한 항목에 T3~T5가 누적.
- 백엔드 구현자는 `git add <자기 경로>`로만 스테이징해 커밋한다(프론트 변경이 동시에 진행 중). Codex(프론트)는 커밋하지 않는다 — 조율자가 커밋.
- 테스트: 백엔드 `cd backend && .venv/bin/python -m pytest tests/ -q`, 프론트 `cd frontend && npx vitest run && npx tsc --noEmit`.

### Task 1: verdict BC 정리 — 부동산 판정 제외 + 상권 축소를 참고 신호로 (백엔드)

스펙 §7. 파일: `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py`(`EXCLUDED_INDUSTRIES`에 `real_estate`, 신규 `ADVISORY_SIGNAL_KEYS = frozenset({"shrinking"})`), `domain/services/rules.py`(`strong_count`·`on_count`·`evaluable_count`가 참고 신호를 건너뜀 — 판정 신호 4개 기준), 관련 테스트(`tests/test_verdict_rules.py`·`test_verdict_thresholds.py`·`test_verdict_gateways.py`·`test_verdict_build.py` 등 제외 6종·12업종 반영), CLI·크론 문구의 "13업종" → "12업종".
완료 기준: pytest green(TDD — 규칙 테스트를 먼저 Red로), 실DB 배치 1회 재실행(`.venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts`, prune이 부동산 427행을 지워 12×427=5,124행), 백테스트 재실행(`… backtest_verdicts --as-of 2022-06-30 --out ../docs/verdict-backtest.md`), 설계서 `2026-09-28-verdict-card-design.md` §13 끝에 재실행 결과 한 줄, HANDOFF §0-12 A의 "신호 재편 결정"·"부동산·헬스장" 항목을 [x]로(헬스장은 원천 정상 확인으로 유지), BE 로그 v0.44.0 항목 생성. 커밋은 `git add backend docs`.

### Task 2: agent BC — verdict 도구 2개·섹션 5개 재편·프롬프트·budget (백엔드)

스펙 §5-2·§6. 파일: 신규 `backend/apps/agent/adapter/outbound/gateways/verdict_facts_gateway.py`(verdict 유스케이스 프로세스 내 호출, `finance_facts_gateway.py` 전례; 판정 없음·대상 아님은 `{"available": false, "reason": ...}`), `app/use_cases/agent_tools.py`(스테이지 `verdict` 도구 `get_verdict`·`get_verdict_alternatives`, 스테이지 순서 verdict → market → shock → funding), `app/use_cases/analysis_interactor.py`(`_SECTIONS` 5개 = verdict "판정"·reasons "왜 안 되나"·conditions "그래도 한다면"·alternatives "대안 동네·업종"·funding "대안 업종 지원사업"; SYSTEM_PROMPT 규칙·섹션별 출력 계약 갱신), `adapter/inbound/api/schemas/analysis_schema.py`(`budget: int | None`)와 라우터·인터랙터로 전달(finance 도구 기본값), `dependencies/analysis_dependencies.py` 배선, `adapter/inbound/cli/agent_eval_scoring.py` 기대 섹션 튜플, `domain/entities/agent_event_entity.py` docstring. 테스트: `tests/test_agent_tools.py`(도구 2개·available false·스테이지), `test_agent_loop.py`(섹션 5개 순서·누락 채움), `test_agent_router.py`(budget 수용·기존 요청 호환), `test_agent_eval_scoring.py`.
완료 기준: pytest green(TDD), `POST /analysis` 기존 요청(budget 없음) 호환, BE 로그 v0.44.0 항목에 누적. 커밋은 `git add backend`. 실 LLM 호출은 하지 않는다(Fake LLM 테스트 전례).

### Task 3: 지도 재편 — 판정 단계구분도만, 지표·연도·분기 제거 (프론트, Codex)

스펙 §3·§6. `lib/map-state.ts`(`MapState = {industry, region, budget}`, 옛 `metric`·`year`·`year_quarter` 파라미터 무시), `control-bar.tsx`(업종 select만), `map-view.tsx`(항상 `verdict`), `map-legend.tsx`(판정만), `lib/metric-sources.ts`(verdict만), `hooks/use-map-data.ts`, `map-page.tsx`, 그리고 소비자가 없어진 `metric-coverage`·`metric-color`의 numeric 부분·`api.ts` fetcher·해당 테스트 삭제. mock 라우트는 남긴다. 관문 `intent-url`·`intent-gate` 테스트에서 metric 관련 기대만 정리.
완료 기준: Vitest 전체·`tsc --noEmit` clean, `/map?region&industry&budget`와 옛 파라미터 포함 URL 모두 동작, FE 로그 v0.31.0 항목 생성. 커밋 금지.

### Task 4: brief 재편 — 사이드패널 한 화면 (프론트, Codex)

스펙 §4·§7(프론트 `VERDICT_EXCLUDED_INDUSTRIES`에 `real_estate` 추가). `side-panel.tsx`(순서: 헤더 → `VerdictSection` → `NeighborhoodLine`(신규) → `ClosedStoresToggle` → CTA "AI 분석 리포트 보기" `/analysis?region&industry&budget` + "자금 계획 →"), `verdict-section.tsx`(켜진 신호 최대 3개, "근거 보기" 제거, 참고 신호 `shrinking` 회색 한 줄), `neighborhood-line.tsx`(신규, 최신 분기 프로필 → "{유형 이름} · {시간대 문장}", 툴팁 `type_reason`, 프로필 없으면 null), 편의점은 `ConvenienceSummarySection` + 안내 한 줄. 제거: `neighborhood-profile`·`time-block-bars`·`hour-gap-chart`·`staying-power`·업종 실적 카드·`GradeBadge` 소비처·`childcare-summary`(도달 불가)와 그 테스트·훅·fetcher(소비자 없으면). `fetchRegionSummary`는 헤더용으로 유지.
완료 기준: Vitest·tsc clean, `side-panel.test.tsx`가 새 순서·CTA href(budget 포함)를 고정, `verdict-section.test.tsx`가 3개 상한·참고 줄을 고정, FE 로그 v0.31.0 항목에 누적. 커밋 금지.

### Task 5: 리포트 — URL 자동 시작·섹션 5개·verdict 스테이지·mock SSE (프론트, Codex)

스펙 §5-1·§6. `analysis-page.tsx`(URL `region`·`industry` 있으면 즉시 `start`, 접힌 헤더 + "다시 분석", 신규 `analysis-page.test.tsx`), `analysis-form.tsx`(직접 방문 폼 유지), `hooks/use-agent-report.ts`(`budget` 전달), `report-view.tsx`(`SECTION_ORDER` 5개, 빈 상태 아웃라인), `lib/agent-events.ts`·`progress-panel.tsx`(`AGENT_NAMES`에 `verdict`, 라벨 "판정 읽기", 도구 `get_verdict`·`get_verdict_alternatives`, 순서 verdict → market → shock → funding), `shared/api/types.ts`(`AgentName`·섹션 키), mock `/api/mock/analysis` 픽스처(`fixtures.agentEventScript`)와 계약 테스트 갱신.
완료 기준: Vitest·tsc clean, FE 로그 v0.31.0 항목에 누적. 커밋 금지.

### Task 6: 통합 확인·문서 (조율자)

실 API(3200 → 8201)로 `/map?region=1168064000&industry=korean_food` → brief → "AI 분석 리포트 보기" → `/analysis` 자동 시작까지 curl/테스트로 확인(브라우저는 사용자 노트북). HANDOFF §0-12 A "관문 → 판정 착지"·"에이전트 리포트 verdict 섹션" [x], STATUS §5-2 프론트 설명 갱신, 커밋.
