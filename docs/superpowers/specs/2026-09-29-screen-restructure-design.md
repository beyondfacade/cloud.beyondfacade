# 화면 재편 — 지도는 경고 한 장, brief는 한 화면, 상세는 AI 리포트 (2026-09-29)

> HANDOFF §0-4·§0-10 "첫 화면 = 판정" 완성. 팀장 결정(9/29): **A안 — 지도 지표 8개 선택기를 없앤다.**
> 이 설계서는 화면 재편만 다룬다. ML(risk BC)은 별도 설계서. 전제: 판정 카드·대안·백테스트(설계서 `2026-09-28-verdict-card-design.md` §1~§13) 완료 상태(BE v0.43.0 · FE v0.30.0).

## 1. 문제

지도 컨트롤바에 지표 8개(동네 유형·심야 체류·음식/유흥 비중·영업 지속 개월·폐업률·성장률·점포수·창업 경고)와 연도·분기 select가 나란히 있고, 동을 누르면 사이드패널에 판정·프로필·시간대·시간대 불일치·영업 지속·업종 실적이 세로로 길게 쌓인다. 사용자가 지표를 골라 가며 비교하는 화면이지 답을 주는 화면이 아니다. AI 분석(`/analysis`)은 별도 폼에서 다시 입력해야 하고 판정 BC를 읽지 않아 LLM이 판정을 자유 서술한다.

## 2. 결정 (3층 구조)

| 층 | 역할 | 내용 |
|---|---|---|
| 지도 `/map` | 경고 한 장 | 업종을 고르면 **판정 단계구분도만**. 지표·연도·분기 select 없음. 폐업 마커 토글은 유지 |
| brief (사이드패널) | 한 화면 요약 | 동 이름·업종 → 판정 배지 → 켜진 신호 최대 3줄 → 대안 2줄 → 동네 한 줄 → 폐업 마커 토글 → **"AI 분석 리포트 보기"** 큰 버튼 + 자금 계획 링크. 스크롤 없이 끝난다 |
| 리포트 `/analysis` | 상세 전부 | URL에 동·업종이 있으면 폼 없이 **바로 시작**. 섹션: 판정 → 왜 안 되나 → 그래도 한다면 → 대안 동네·업종 → 대안 업종 지원사업. 판정·대안은 verdict BC를 **도구로 읽고** 문장만 LLM |

지도 지표 8개의 데이터는 사라지지 않는다 — 리포트 "왜 안 되나"에서 에이전트 도구(`get_region_metrics`·`get_neighborhood_profile`·상권변화)가 숫자로 인용한다. 프론트 단계구분도 코드는 판정만 남긴다.

## 3. 지도 `/map`

- `MapState` = `{industry, region, budget}`. `metric`·`year`·`year_quarter`는 상태에서 제거. `parseMapState`는 옛 URL의 그 파라미터를 **무시**(400·리다이렉트 없음).
- `ControlBar` = 업종 select 하나(+ 기존 모바일 컨트롤). 지표 무리 버튼·연도·분기 select 삭제.
- `MapView`는 항상 `verdict` 지표(축 `industry_latest`). 판정 제외 업종(편의점·부동산 — §7)은 현행 `isVerdictMissingForIndustry` 경로: 색 없음 + 배너 "판정 준비 중인 업종".
- 범례는 판정 4단계만. 숫자 지표용 `FORMAT_BY_METRIC`·`UNIT_HINT`·numeric scale·`metric-coverage`(연도·분기 클램프)·`METRIC_GROUPS`·`METRIC_SOURCES`의 7개 비판정 항목·`use-map-data`의 numeric 분기 등 **소비자가 없어진 코드는 지운다**(CLAUDE.md §3 — 내 변경이 만든 미사용 코드). `lib/quarters.ts`는 §4 "동네 한 줄"이 최신 분기를 구하는 데 쓰면 남긴다.
- mock 라우트(`/api/mock/metrics`·`profiles`·`commerce-changes`·`hour-gaps`)는 실 API의 미러라 **남긴다**(§15). 프론트 `api.ts`의 fetcher는 소비자가 없으면 지운다.
- 관문(`intentToUrl`)은 이미 `/map?region&industry&budget`만 보내므로 **기본 화면이 자동으로 판정**이 된다(§0-12 "관문 → 판정 착지" 해소). `DiagnosisLine` 링크 문구 "지도에서 확인 →"은 유지.

## 4. brief (사이드패널)

위에서 아래로, 이 순서 그대로:

1. 헤더: 동 이름 · 동 코드 · 업종 (현행).
2. `VerdictSection` — 배지 + **켜진 신호 최대 3개**(strong 먼저, 현행 정렬) + `VerdictAlternatives` 2줄(현행). **"근거 보기" 토글과 신호 5개 전체 목록은 제거**(리포트로 이동). 보류·경고 없음 한 줄 안내는 유지. 상권 축소가 켜지면(§7 참고 신호) 켜진 신호 목록이 아니라 그 아래 회색 한 줄 "참고: 서울시 상권변화지표 '상권축소' (2026년 2분기)".
3. **동네 한 줄** (신규 `NeighborhoodLine`): `{유형 이름} · {시간대 문장}` 예: "낮 인구 우위형 · 점심·오후가 하루의 정점". 원천은 최신 분기 `region_profile`(`useRegionProfile(region, latestQuarter)`; API가 분기를 요구하면 `lib/quarters`의 최신 분기). 프로필 없으면 줄 자체를 그리지 않는다. 툴팁에 `type_reason`.
4. `ClosedStoresToggle` (현행).
5. CTA: 주 버튼 **"AI 분석 리포트 보기"** → `/analysis?region=&industry=&budget=`(예산도 넘긴다), 보조 링크 "자금 계획 →" `/plan?…`(현행).

제거: `NeighborhoodProfileSection`(상세 수치 5줄)·`TimeBlockSection`·`HourGapSection`·`StayingPowerSection`·"업종 실적" 카드 목록·`GradeBadge` 소비처·`INDUSTRY_SECTIONS`의 `childcare`(어린이집은 업종 select에 없어 도달 불가). **편의점은 예외**: 판정이 없으므로 brief 본문 = `ConvenienceSummarySection` 한 줄 요약 + "판정은 담배권 특화 신호 단계에서 제공" 안내. `fetchRegionSummary`는 헤더 이름용으로만 남기고 cards는 안 쓴다(응답 계약은 불변).

## 5. 리포트 `/analysis`

### 5-1. 프론트
- `analysis-page`: URL `region`·`industry`가 모두 있으면 마운트 즉시 `start({region, industry, budget?})`. 폼은 접힌 헤더 "역삼1동 · 한식 · 예산 N만원"과 "다시 분석" 버튼, 추가 질문 입력은 선택. 직접 방문(파라미터 없음)이면 현행 폼.
- `SECTION_ORDER` = `["verdict","reasons","conditions","alternatives","funding"]`. 섹션 제목은 백엔드 마크다운 `###` 헤더 그대로(현행). 빈 상태 아웃라인도 이 5개로.
- `AGENT_NAMES`에 `"verdict"` 추가(라벨 "판정 읽기", 도구 목록 `get_verdict`·`get_verdict_alternatives`). 나머지 market/shock/funding 라벨은 유지하되 progress-panel 순서는 verdict → market → shock → funding.
- mock `/api/mock/analysis` SSE 픽스처(`fixtures.agentEventScript`)는 새 섹션 키·verdict 스테이지로 갱신. 타입 `AgentName`·`AgentEvent`·섹션 키는 `shared/api/types.ts` 단일 원천.

### 5-2. 백엔드 (agent BC)
- 신규 `adapter/outbound/gateways/verdict_facts_gateway.py` — verdict BC 유스케이스를 **프로세스 내 호출**(finance_facts_gateway 전례): `verdict(region, industry)` → 카드 전 필드(신호 5개·근거·백분위·산출일), `alternatives(region, industry)` → 두 축. 판정 없음·대상 아님은 예외를 잡아 `{"available": false, "reason": "..."}`로 돌려준다(LLM이 "판정 없음"을 그대로 쓰도록).
- 도구 2개 `get_verdict`·`get_verdict_alternatives`(스테이지 `verdict`, 다른 스테이지보다 **먼저**).
- `_SECTIONS` = `(verdict "판정", reasons "왜 안 되나", conditions "그래도 한다면", alternatives "대안 동네·업종", funding "대안 업종 지원사업")`. 도구 스테이지 매핑: verdict→verdict, market·shock→reasons, finance(계산기·임대)→conditions, funding→funding. `alternatives` 섹션은 verdict 스테이지 결과로 쓴다(추가 도구 없음).
- `SYSTEM_PROMPT` 규칙 추가: **"판정 등급·켜진 신호·대안은 `get_verdict`/`get_verdict_alternatives` 값을 그대로 옮긴다. 등급을 바꾸거나 신호를 새로 만들거나 🟢 추천을 쓰지 않는다. 판정이 없으면 '판정 없음'이라 쓰고 이유를 붙인다."** 섹션별 출력 계약: 판정(배지 한 줄 + 켜진 신호 목록 + 산출일), 왜 안 되나(신호별 근거 문장 + 지표 숫자 + 충격·뉴스 악재), 그래도 한다면(시간대 조건·임대료 상한·손익분기 매출), 대안(두 축 각 3개, 없으면 "대안 없음"), 지원사업(대안 업종 우선).
- `split_report_sections`·누락 섹션 채움·`report_done`·저장(`report_md` 통째)은 현행. `agent_eval_scoring.py`의 기대 섹션 튜플도 갱신.
- 세션 파라미터에 `budget`(선택)이 오면 finance 도구 기본값으로 쓴다(스키마 `AnalysisCreateRequest.budget: int | None`).

## 6. 계약 표 (프론트 ↔ 백엔드, 두 작업자가 각자 지킬 것)

| 항목 | 값 |
|---|---|
| 섹션 키·순서 | `verdict, reasons, conditions, alternatives, funding` |
| 섹션 제목(`###`) | 판정 / 왜 안 되나 / 그래도 한다면 / 대안 동네·업종 / 대안 업종 지원사업 |
| 스테이지(`agent_status.agent`) | `orchestrator, verdict, market, shock, funding` |
| 도구 이름 | `get_verdict`, `get_verdict_alternatives` (+ 기존 10개) |
| `POST /analysis` | `{region, industry, question?, model?, budget?}` |
| `/map` URL | `?region&industry&budget` (metric·year·year_quarter 무시) |
| `/analysis` URL | `?region&industry&budget` |

## 7. verdict BC 정리 두 건 (착수 전 반나절)

- **부동산 판정 제외**: `EXCLUDED_INDUSTRIES`에 `real_estate` 추가(원천에 폐업 이력 없음 — 브이월드 API·공공데이터 파일·서울 열린데이터 모두 현재 사무소만. 조사 9/29). 프론트 `VERDICT_EXCLUDED_INDUSTRIES`에도 추가. 배치 재실행(prune이 옛 행 삭제). 판정 대상 12종.
- **상권 축소 = 참고 신호**: 백테스트 lift 0.96×(무신호). 신호는 그대로 평가·저장하되 **등급 계산에서 뺀다** — `ADVISORY_SIGNAL_KEYS = {"shrinking"}`(entity), `rules.strong_count/on_count/evaluable_count`가 이 키를 건너뛴다. `min_evaluable` 가드는 **3 → 2로 내린다**(판정 신호 4개 중 2개) — 3/4로 두면 판정 대상의 70.6%가 보류가 되는데, 상권 축소는 예측력이 없었으므로 옛 3/5도 사실상 2신호 판정이었다(9/29 결정, 보류 70.6% → 39.3%). 카드·리포트는 "참고" 표기. 백테스트 CLI 재실행해 결과 문서 갱신.
- 두 건 다 테스트 갱신 + 버전 로그(BE) + HANDOFF §0-12 체크.

## 8. 구현 순서·분담

| # | 작업 | 담당 | 의존 |
|---|---|---|---|
| T1 | §7 verdict 정리(부동산 제외·참고 신호·배치·백테스트 재실행) | 클로드 서브에이전트 (BE) | 없음 |
| T2 | §5-2 agent BC: verdict 도구·섹션 재편·프롬프트·budget·평가 튜플 | 클로드 서브에이전트 (BE) | 없음 (T1과 병행) |
| T3 | §3 지도 재편 + 미사용 코드 제거 | **Codex** (FE) | 없음 |
| T4 | §4 brief 재편(+부동산 제외 set) | **Codex** (FE) | T3 |
| T5 | §5-1 리포트 자동 시작·섹션·스테이지·mock SSE | **Codex** (FE) | T3 (계약 표 §6만 알면 T2와 병행) |
| T6 | 통합 확인: 실 API로 `/map`→brief→`/analysis` 왕복, 버전 로그·HANDOFF·STATUS 갱신 | 클로드 | T1~T5 |

버전: BE **v0.44.0**(T1+T2 합산, 로그는 T1·T2가 각자 항목 추가), FE **v0.31.0**(T3~T5 합산, 한 항목에 누적).
커밋은 작업 단위로 조율자(클로드)가 한다. Codex는 커밋하지 않는다.

## 9. 테스트

- FE: 삭제되는 컴포넌트·lib의 테스트는 함께 삭제. 남는 것: `map-state`(3필드·옛 파라미터 무시), `control-bar`(업종만), `map-view`(항상 verdict), `map-legend`(판정만), `side-panel`(새 순서·CTA href에 budget), `verdict-section`(최대 3개·근거 보기 없음·참고 줄), `neighborhood-line`(신규), `analysis-page`(URL 자동 시작 — 신규), `report-view`(5섹션), `progress-panel`(verdict 스테이지), `agent-events`, mock analysis 계약, `intent-gate`(metric 파라미터 없음). 전체 Vitest·`tsc --noEmit` clean.
- BE: `test_verdict_rules`(참고 신호 제외)·`test_verdict_thresholds`(제외 6종)·`test_verdict_gateways`(12종)·`test_agent_tools`(도구 2개·available false)·`test_agent_loop`(섹션 5개 순서·누락 채움)·`test_agent_router`(budget)·`test_agent_eval_scoring`. 전체 pytest green.

## 10. 이 문서가 결정하지 않는 것

- ML(risk BC) — 별도 설계서. 카드 모양은 유지되므로 판정 원천만 바뀐다.
- 대안 항목 클릭 시 지도 이동·업종 전환 — 후속.
- 리포트 안 작은 지도 조각(동네 유형 등 옛 단계구분도의 재활용) — 필요해지면 후속.
- 편의점 판정(담배권 특화 신호, §0-7 4번).
