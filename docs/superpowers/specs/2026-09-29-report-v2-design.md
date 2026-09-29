# 리포트 v2 — 사실 선수집·시각 자료·토큰 스트리밍 (2026-09-29)

> 팀장 지적(9/29): AI 분석이 너무 느리고 죄다 글이라 유저 친화적이지 않다. 실측 결과 원인은 데이터 양이 아니다.
> 전제: 화면 재편(`2026-09-29-screen-restructure-design.md`) 완료 상태. 1단계(SSE 프록시 스트리밍 복구)는 그 브랜치에 먼저 붙인다(§8-0).

## 1. 실측 (9/29 정오, 역삼1동)

| 원인 | 측정 |
|---|---|
| Next rewrite 프록시가 SSE를 끝까지 버퍼링 | 3200 경유: 이벤트 23개가 19.7초에 한꺼번에. 8201 직접: 0·1.9·6.8초 순차 |
| LLM 왕복 3~5회 + 본문 3~4k 토큰 한 덩어리 생성 | 최근 8건 14~58초(gemini-2.5-flash). 입력 13~33k 토큰은 턴마다 대화 전체를 다시 보내는 누적 |
| 도구 데이터 | 12개 도구 합계 19k자(≈1만 토큰), 각 0.2초 이내 — **원인 아님** |
| 도구 호출이 LLM 재량 | 같은 입력에서 판정 도구만 부르고 6.8초에 끝난 실행과 8개 도구를 부른 실행이 섞임 → 섹션 품질 편차 |

## 2. 결정

1. **사실은 코드가 모으고, LLM은 글만 쓴다.** 리포트에 필요한 사실(판정·대안·지표·프로필·시간대·상권변화·인구·충격·뉴스·지원사업 후보)은 LLM 호출 전에 백엔드가 직접 조회해 **`facts` 이벤트**로 먼저 내보내고, 같은 사실을 LLM 첫 메시지에 넣는다. 도구 루프는 남기되 "facts에 없는 것"에만 쓴다(사실상 finance 2종·RAG 재검색).
2. **시각 자료는 `facts`로 즉시 그린다.** 프론트는 `facts`를 받는 순간 판정 카드·신호 막대·대안 카드·동네 프로필·하루 흐름·시간대 불일치·영업 지속·8분기 추세선·지원사업 카드를 렌더한다. LLM 문장은 각 시각 자료 아래에 스트리밍된다. 글이 늦어도 화면은 0.5초 안에 찬다.
3. **본문은 토큰 단위로 흘린다.** `LLMGatewayPort.stream()`을 추가하고, 마커 `[SECTION:name]`을 스트림에서 잘라 `report_delta`를 문장 조각 단위로 보낸다.
4. 판정·대안은 여전히 verdict BC 값 그대로(§0-10 "판정은 규칙, 문장은 LLM"). 프롬프트의 "도구를 먼저 불러라" 문장들은 facts가 대신하므로 **삭제**하고 "facts 값을 그대로 옮긴다"로 바꾼다.

## 3. 백엔드 (agent BC)

### 3-1. `facts` 수집 — `ReportFactsCollector`(app/use_cases/report_facts.py)
- 입력 `(region, industry, budget)`. 기존 Driven Port를 그대로 쓴다: `VerdictFactsPort.verdict/alternatives`, `RegionFactsPort.metrics/summary/population/neighborhood_profile/shocks`, `FundingFactsPort.candidates`, RAG 뉴스 검색(현행 `search_news` 도구가 쓰는 유스케이스), 신규 `RegionFactsPort.metrics_history(region, industry)`(연도별 store_count·open/close_count·closure_rate·growth_rate, `region_industry_metric` 2019~최신), `RegionFactsPort.hour_gap(region, industry)`(현행 metric BC `hour-gaps` 최신 분기), `RegionFactsPort.commerce_change_detail(region)`(현행 neighborhood BC 최신 분기 + 서울 베이스라인).
- 각 항목은 독립 try/except — 하나가 실패해도 나머지는 나간다. 실패 항목은 `{"available": false, "reason": ...}`.
- 출력 `ReportFacts`(dataclass → dict):
  ```
  {region:{code,name,industry_id,industry_name}, verdict, alternatives, profile, hour_gap, commerce_change,
   metrics_history:[{year, store_count, open_count, close_count, closure_rate, growth_rate}], population,
   shocks:[...], news:[...], funding_candidates:[...], budget}
  ```
- 수집 시간 목표 0.5초 이내(전부 DB 조회·로컬 RAG).

### 3-2. 이벤트 계약 (추가·변경)
| 이벤트 | payload | 시점 |
|---|---|---|
| `facts` (신규) | `ReportFacts` dict 전체 | orchestrator running 직후, LLM 호출 전 |
| `agent_status` | 스테이지 `orchestrator, facts, writer` (+ 도구를 실제로 부른 경우에만 `market/shock/funding`) | facts running→done은 수집 전후, writer running→done은 LLM 생성 전후 |
| `report_delta` | `{section, markdown}` — 이제 **조각 단위**(수십 자), 같은 section이 여러 번 온다 | 스트리밍 중 |
| `report_done` | 현행 | 끝 |
`AgentName`에 `facts`·`writer`가 추가되고 `verdict` 스테이지는 사라진다(판정은 facts 안). 프론트 리듀서는 이미 `report_delta`를 append 하므로 조각 단위에 대응된다.

### 3-3. 인터랙터 흐름 (run)
1. `orchestrator running` → `facts running` → 수집 → `facts` 이벤트 → `facts done`.
2. 메시지 = system(축약 프롬프트) + user(`[FACTS] {json}` + 질문). 도구 스펙은 finance 2종·`search_news`·`search_funding`만 남긴다(나머지는 facts가 대체).
3. `writer running` → `self._llm.stream(messages, specs)`를 소비: 텍스트 조각은 `SectionSplitter`(domain/services/section_stream.py, 순수)가 마커 기준으로 `(section, chunk)`를 내고 `report_delta`로 방출. 도구 호출이 오면 현행 루프대로 실행하고 다음 턴(스트림) 재개. 한 번도 마커가 안 나온 텍스트는 `verdict` 앞 서문으로 간주해 버린다.
4. 스트림 종료 후 누락 섹션은 현행 폴백("분석 데이터가 부족합니다") — 단 판정·대안 섹션은 facts가 있으면 **코드가 facts로 채운다**(LLM이 안 써도 판정은 나간다).
5. `writer done` → `orchestrator done` → `report_done`. 저장(`report_md`)은 조각을 섹션별로 이어 붙인 결과.

### 3-4. `LLMGatewayPort.stream()`
- `stream(messages, tools) -> Iterator[LLMStreamEvent]`, `LLMStreamEvent = text(str) | tool_calls(list[LLMToolCall]) | usage(LLMUsage)`(dataclass 3종 또는 kind 필드 하나).
- Gemini: `generate_content_stream`, 조각의 `text`·마지막 `function_calls`·`usage_metadata`. Ollama: `stream: True` NDJSON. Fallback: primary 스트림이 첫 조각 전에 실패하면 secondary로, **첫 조각 이후 실패는 그대로 예외**(반쯤 쓴 글을 다른 모델이 이어 쓰지 않는다 — 인터랙터가 폴백 섹션으로 마무리).
- 기존 `chat()`은 남긴다(재프롬프트·평가 러너가 쓴다).

### 3-5. 프롬프트
- 규칙 ⑤를 "판정·대안·지표는 `[FACTS]`의 값을 그대로 옮긴다. 도구는 facts에 없는 것에만 쓴다(`run_finance_simulation`은 13개 입력이 있을 때만)"로 축약. "가장 먼저 호출한다"·"반드시 호출한다" 문장 삭제.
- 섹션 계약 5개는 유지하되 도구 이름을 facts 키로 바꾼다(`get_verdict` → `facts.verdict` 등). 시각 자료가 숫자를 보여주므로 본문 계약에 **"표·숫자 나열 대신 해석 2~4문장"** 을 명시 — 글이 짧아져야 빨라진다(출력 토큰 목표 1.5k 이하).
- `agent_eval_scoring` 기대 섹션은 그대로(5개).

### 3-6. API·저장
- `POST /analysis`·`GET /analysis/{id}/events` 경로·`AnalysisCreateRequest` 불변. `analysis_report` 스키마 불변(마이그레이션 없음). facts는 저장하지 않는다(§10).

## 4. 프론트 (agent-report)

### 4-1. 타입·리듀서
- `shared/api/types.ts`: `AgentEvent`에 `{type:"facts", facts: ReportFacts}` 추가, `ReportFacts` 타입(3-1과 동일 키), `AgentName = orchestrator|facts|writer|market|shock|funding`.
- `lib/agent-events.ts`: `AgentState.facts: ReportFacts | null`; `facts` 이벤트로 저장. `report_delta` append는 현행.

### 4-2. 리포트 레이아웃 — 섹션마다 "그림 위·글 아래"
| 섹션 | 시각 자료(facts로 즉시) | 글(스트리밍) |
|---|---|---|
| 판정 | `VerdictCard`(배지·켜진 신호·참고 신호·산출일 — brief의 `VerdictSection`과 같은 어휘, `shared/ui/verdict-card.tsx`로 승격해 brief와 공유) + `SignalBars`(신호 5개 백분위 가로막대, 75/90 기준선) | 배지 한 줄 해석 |
| 왜 안 되나 | `MetricTrend`(점포수·폐업률·성장률 8년 꺾은선, `metrics_history`) · `NeighborhoodProfileCard`·`StayingPower`(복원) · `ShockList` | 신호별 2~4문장 |
| 그래도 한다면 | `TimeBlockBars`·`HourGapChart`(복원) | 시간대 조건·임대료·손익분기 안내 |
| 대안 동네·업종 | `AlternativesCards`(두 축, 각 최대 3, 판정 배지) | 한 줄 |
| 대안 업종 지원사업 | `FundingCards`(후보 카드: 기관·요약·대상·링크) | 해당 가능성 안내 |
- 복원 대상 4종은 git `v0.30.0`(커밋 82505a8 이전)의 `neighborhood-profile.tsx`·`time-block-bars.tsx`·`hour-gap-chart.tsx`·`staying-power.tsx`. 훅 대신 **props로 facts를 받도록** 고쳐 `features/agent-report/components/charts/`에 둔다(다른 feature가 안 쓰므로 shared 아님; `VerdictCard`만 brief와 공유하므로 `shared/ui`).
- 차트 라이브러리는 추가하지 않는다 — 기존 막대는 CSS, 꺾은선은 인라인 SVG(토큰 색, dataviz 팔레트 주석).
- 글이 아직 없는 섹션은 시각 자료 + 스켈레톤 한 줄. `facts.<key>.available === false`면 그 그림 자리에 "자료 없음" 한 줄.
- 진행 패널: 스테이지 `facts`("사실 수집")·`writer`("리포트 작성") 라벨, 도구 스테이지는 실제로 열릴 때만 표시.

### 4-3. mock
- `/api/mock/analysis/[id]/events`: `facts` 이벤트(결정적 픽스처 — `verdictOf`·`alternativesOf`·`regionProfileOf`·`hourGapOf`·`commerceChangeDetailOf`·`metricRows` 재사용) → `report_delta` 조각 여러 개(문장 단위 분할) → `report_done`. 계약 테스트 갱신.

## 5. 계약 표

| 항목 | 값 |
|---|---|
| 이벤트 | `agent_status, tool_call, facts, report_delta, report_done` |
| 스테이지 | `orchestrator, facts, writer, market, shock, funding` |
| `facts` 키 | `region, verdict, alternatives, profile, hour_gap, commerce_change, metrics_history, population, shocks, news, funding_candidates, budget` |
| 섹션 | `verdict, reasons, conditions, alternatives, funding` (불변) |
| `report_delta` | 조각 단위, 같은 section 반복 가능, 프론트는 append |

## 6. 성능 목표 (역삼1동 한식, gemini-2.5-flash)
- 첫 이벤트 < 0.2초, `facts` < 0.7초(시각 자료 전부 표시), 첫 `report_delta` < 4초, `report_done` < 20초(출력 1.5k 토큰 기준). 측정은 `scripts/`의 SSE 타임라인 스크립트(백엔드 `apps/agent/adapter/inbound/cli/sse_timeline.py`, 신규)로 한다.

## 7. 테스트
- BE: `ReportFactsCollector`(항목별 실패 격리·키 완전성), `SectionSplitter`(마커가 조각 경계에 걸칠 때·마커 없는 서문·중복 마커), 인터랙터(facts 이벤트 순서·조각 report_delta·판정 섹션 facts 폴백·도구 턴 재개, Fake 스트림 LLM), Gemini/Ollama `stream()` 어댑터(SDK 스텁), Fallback(첫 조각 전/후 실패), 라우터(이벤트 프레임). 전체 pytest green.
- FE: 리듀서 `facts`, 리포트 뷰(facts만으로 그림이 뜨고 글은 나중에 붙음·available false 처리), 차트 4종 복원 테스트(props 기반), `VerdictCard` 공유(brief 테스트 유지), mock 계약, `tsc` clean.

## 8. 구현 순서·분담

- **8-0 (선행, 화면 재편 브랜치)**: SSE 프록시 Route Handler(Codex, 진행 중).
- 새 브랜치 `feat/report-v2` (화면 재편 머지 후 또는 그 위에서 분기).

| # | 작업 | 담당 |
|---|---|---|
| T1 | `RegionFactsPort` 확장 3종(metrics_history·hour_gap·commerce_change_detail) + `ReportFactsCollector` + `facts` 이벤트 + 프롬프트 축약 + 판정 섹션 facts 폴백 (스트리밍 전, 현행 `chat()` 유지) | 클로드 BE |
| T2 | `LLMGatewayPort.stream()` + Gemini/Ollama/Fallback 스트림 + `SectionSplitter` + 인터랙터 스트리밍 전환 + `sse_timeline.py` | 클로드 BE |
| T3 | 타입·리듀서·진행 패널·mock SSE(facts+조각) | Codex FE |
| T4 | 시각 자료: `VerdictCard` 승격·`SignalBars`·`AlternativesCards`·`FundingCards`·`MetricTrend`·차트 4종 복원·리포트 레이아웃 | Codex FE |
| T5 | 통합: 타임라인 측정(§6 목표), 문서·버전 로그(BE v0.45.0 · FE v0.32.0) | 클로드 |

T1→T2 순차, T3→T4 순차, BE/FE 병행. T3는 §5 계약 표만으로 시작 가능.

## 9. 리스크
- Gemini 스트리밍에서 function_calls가 조각 끝에만 온다 — 텍스트 조각을 먼저 흘린 뒤 도구 호출이 오면 그 텍스트는 "도구 전 서문"이라 버려야 할 수 있다 → `SectionSplitter`는 마커 전 텍스트를 버리므로 자연히 처리. 마커 뒤에 도구 호출이 오는 경우는 프롬프트로 금지("섹션을 쓰기 시작하면 도구를 부르지 않는다").
- 로컬 gemma4 폴백은 스트림에서도 느리다(39초 실측) — 목표는 Gemini 기준.
- facts JSON이 20k자 — SSE 한 프레임으로 충분. 프롬프트 입력은 현행보다 줄어든다(누적 턴이 사라짐).

## 10. 결정하지 않는 것
- facts 영속화(리포트 재열람) — `analysis_report.facts_json` 컬럼은 재열람 화면이 생길 때.
- finance 프리필 도구(손익분기 자동 계산) — HANDOFF §0-12 A 후속 그대로.
- 리포트 안 작은 지도 조각.

## 11. 실측 결과 (2026-09-29 오후, `sse_timeline`, 역삼1동)

| 구간 | v1 (재편 직후) | v2 (T1~T2 + thinking 끔) | 목표 |
|---|---|---|---|
| 첫 이벤트 | 19.7s (프록시 버퍼링) → 0.0s (8-0 후) | 0.03~0.06s | 0.2s |
| facts | — | 0.17~0.18s (웜) · 1.45s (백엔드 reload 직후 콜드, RAG 임베딩) | 0.7s |
| 첫 report_delta | 14.9~17.5s | **1.4~2.8s** | 4s |
| report_done | 24.9~25.7s | **13.3s** (한식+예산, 4.3~4.7k자) · **8.7s** (카페, 2.9k자) | 20s |

- 결정적 레버는 Gemini 2.5 Flash `thinking_budget=0`(같은 프롬프트로 첫 토큰 11.7→1.1s, 완료 22.5→8.5s). 스트리밍 코드 경로엔 지연 요소 없음(리뷰어가 SDK 대조).
- SSE 프레임은 리포트당 약 50~75개(Gemini가 문장 덩어리로 줌) — 코얼레싱 불필요.
- 남은 것: 콜드 facts 1.45s(임베딩 모델 워밍업·뉴스 캐시 후보), 도구 턴이 끼면 `_MIN_REQUEST_INTERVAL_SECONDS=4.0`이 글쓰기 턴을 4초 지연(무료 티어 보호 상수), `split_report_sections`는 테스트만 소비.
