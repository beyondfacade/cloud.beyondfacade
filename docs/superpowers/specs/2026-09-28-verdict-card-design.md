# 판정 카드 — 공통 신호 5개 · 위험도 지도 · 폐업 마커 설계

> 작성 2026-09-28 · 백엔드 v0.39.0 / 프론트 v0.28.0 기준
> 선행 문서: `docs/HANDOFF.md` §0-2(신호 → 판정 → 대안), §0-7(실행 순서 1번), §0-8(결정), §0-10(상대평가·risk BC), §0-11(학원·어린이집 보조축)
> 선례 코드: `backend/apps/metric/domain/services/typology.py`(분포 기반 임계값 + 규칙 객체 + Verdict), `backend/apps/metric/adapter/outbound/gateways/store_stats_gateway.py`(다른 BC ORM을 읽는 게이트웨이)

## 1. 목적

관문 한 줄("역삼동 카페")의 첫 화면을 **판정 카드** 하나로 만든다. 연도별 폐업률 표를 사용자가 읽게 하지 않고, "이 동네에서 이 장사는 하지 마라"를 켜진 경고 신호와 근거 문장으로 말한다.
이번 범위는 HANDOFF §0-7 실행 순서 **1번**: 공통 신호 5개 → 판정 카드 + 업종별 위험도 지도 + 폐업 마커. 대안 두 축(2번)·백테스트(3번)·업종 특화 신호(4번)는 다루지 않는다.

## 2. 결정 사항 (2026-09-28 브레인스토밍)

| 항목 | 결정 | 이유 |
|---|---|---|
| 판정 산출 | **규칙 신호 5개 + 상대평가**. ML(§0-10 모델 ②)은 백테스트 단계로 미룸 | 지금 데이터로 바로 됨. 신호 값은 뒤에 모델 피처로 그대로 재사용 |
| 임계값 | 업종 안에서 427동 백분위. 절대 기준 없음 | §0-8 결정. 업종별 기저율이 달라 절대값은 못 씀 |
| 위치 | **신규 `verdict` BC** + 새벽 배치 테이블 `region_industry_verdict` | 지도가 427동을 한 번에 칠하므로 요청 시 계산은 무거움. §0-10 risk BC의 자리를 이어받음 |
| 신호 입력 | verdict BC **자체 출력 포트·게이트웨이**가 store·metric·neighborhood ORM을 읽음 | metric BC의 `store_stats_gateway` 선례. 다른 BC 무변경 |
| 범위 | 세 덩어리 전부, **3단계 구현** | §7 |
| 포화 분모 | **상주인구만**(`region_profile.resident_total`) | 프로필에 직장인구 필드가 없고, 직장인구 원천은 11동 결측(STATUS §2-4)이라 0으로 읽힐 위험 |

## 3. 신호 정의

전부 동×업종 단위, **판정 대상 13업종** = 마스터 18업종 − 학원·어린이집(§0-11 보조축) − `restaurant_other`(비노출) − `chicken`(인허가 '통닭' 업태가 2017-09 이후 신규 발급 없음, 업종 확장 설계서 §3-3) − `convenience_store`(스냅샷 전용 원천이라 store 인허가 행이 없어 신호 3개가 영구 불가 — 표본 부족이 아니라 원천 결측이므로 제외, 4단계 담배권 특화 신호 때 재포함, 9/29 Ruling A). 제외 목록은 `IndustryCatalogPort`가 아니라 도메인 상수 `EXCLUDED_INDUSTRIES`로 둔다. 프론트 `INDUSTRIES`는 아직 편의점 포함 14종 — 판정 카드·지도의 제외 반영은 2단계(FE)에서. 배치 실행일 `today` 기준.

### 3-1. 신호 5개

| key | 이름 | 값 | 원천 | 나쁜 방향 | 표본 가드(미달 → 미판정) |
|---|---|---|---|---|---|
| `net_outflow` | 순유출 | (최근 12개월 폐업 − 개업) ÷ 12개월 전 시점 영업중 점포수 | store | 높을수록 | 시작 점포 < 10 |
| `survival_cliff` | 생존 절벽 | 개업일 ∈ [today−4y, today−3y) 코호트 중 3년 생존 비율. 생존 = 폐업일 없음 또는 폐업일 ≥ 개업일+3y | store | 낮을수록 | 코호트 < 10 |
| `early_closure` | 조기 폐업 | 폐업일 ∈ [today−3y, today] 점포의 영업개월(폐업일−개업일) 중위값 | store | 낮을수록 | 폐업 < 10 |
| `saturation` | 포화 | 최신 연말 `store_count`(region_industry_metric, 최신 연도) ÷ (최신 분기 `resident_total` ÷ 1,000) | metric + region_profile | 높을수록 | resident_total < 1,000 또는 결측 |
| `shrinking` | 상권 축소 | 최신 분기 `region_commerce_change.change_code == 'HL'`(상권축소) | neighborhood | 이진 | 해당 동·분기 행 없음 |

`shrinking`은 동 단위라 같은 동의 13업종에 동일하게 켜진다. 업종 무관 신호라는 점을 근거 문장에 밝힌다("동 전체 상권변화지표").

### 3-2. 상대평가 — 레벨 산출

- 업종별로 가드를 통과한 동만 모아 나쁜 방향 백분위 `p`(0~100)를 구한다. 생존율·중위개월처럼 "낮을수록 나쁨"인 값은 부호를 뒤집어 백분위를 낸다.
- **`p ≥ 75` → on, `p ≥ 90` → strong**, 그 외 off. 가드 미달은 `unavailable`.
- `shrinking`: on = 상권축소, strong = 상권축소이면서 `closed_months < seoul_closed_months`(같은 분기 베이스라인). off = 그 외.
- 상수 0.75·0.90은 `VerdictThresholds` dataclass 한 곳(`domain/services/thresholds.py`)에만 둔다. 실제 경계값(예: 한식 순유출 75백분위 = 0.083)은 배치마다 분포에서 재계산하며 어디에도 하드코딩하지 않는다(`typology.py` 원칙).
- 동률 처리: 백분위는 "값보다 작은 동의 비율"(strict)로 계산해 이진값이 섞여도 전부 켜지지 않게 한다.

### 3-3. 판정 규칙

| 판정 | 코드 | 조건 |
|---|---|---|
| 🔴 비추천 | `red` | strong ≥ 2 |
| 🟠 조건부 | `orange` | on 또는 strong이 1개 이상 (red가 아닐 때) |
| ⚪ 경고 없음 | `clear` | 켜진 신호 없음 |
| 판정 보류 | `insufficient` | 판정 가능한 신호(off/on/strong)가 **3개 미만** — 표본 부족 동을 ⚪로 오해하지 않기 위해 |

🟢 추천은 없다(§0-2). 보류 판정은 먼저 검사한다(가능 신호 < 3이면 켜진 개수와 무관하게 보류).

### 3-4. 근거 문장 (evidence)

신호마다 한국어 한 문장을 배치에서 만들어 저장한다. 숫자와 비교 기준을 반드시 넣는다.

- `net_outflow`: "지난 12개월 폐업 41곳 > 개업 28곳 (순유출률 13%, 서울 한식 상위 8%)"
- `survival_cliff`: "3년 전 개업한 한식당 37곳 중 14곳만 남음 (생존율 38%, 서울 한식 하위 6%)"
- `early_closure`: "최근 3년 폐업 한식당의 영업 기간 중위 19개월 (서울 한식 하위 12%)"
- `saturation`: "상주인구 1,000명당 한식당 9.4곳 (서울 상위 4%)"
- `shrinking`: "서울시 상권변화지표 '상권축소' (2026 2분기, 동 전체 기준)"
- 미판정: "표본 부족 — 3년 전 개업 코호트 4곳 (10곳 미만)"

문장은 규칙 코드가 만든다. LLM은 관여하지 않는다(§0-10 "판정은 규칙, 문장은 LLM"의 **문장**은 리포트 서술을 뜻하며 카드의 근거 문장은 결정적이어야 한다).

## 4. verdict BC

### 4-1. 프랙탈 11파일 + 도메인 서비스

```
backend/apps/verdict/
├── adapter/inbound/api/v1/region_industry_verdict_router.py
├── adapter/inbound/api/schemas/region_industry_verdict_schema.py
├── adapter/inbound/mappers/region_industry_verdict_mapper.py
├── adapter/inbound/cli/build_verdicts.py                 ← 배치 진입점 (build_metrics.py와 같은 모양)
├── adapter/outbound/orms/region_industry_verdict_orm.py
├── adapter/outbound/orm_mappers/region_industry_verdict_orm_mapper.py
├── adapter/outbound/repositories/region_industry_verdict_repository.py
├── adapter/outbound/gateways/store_signal_stats_gateway.py   ← store ORM 집계 (순유출·코호트·중위개월)
├── adapter/outbound/gateways/region_context_gateway.py       ← region_industry_metric·region_profile·commerce_change ORM
├── app/dtos/region_industry_verdict_dto.py
├── app/ports/input/region_industry_verdict_use_case.py
├── app/ports/output/region_industry_verdict_port.py          ← Repository / StoreSignalStatsPort / RegionContextPort / IndustryCatalogPort (ISP, 파일은 하나, 클래스는 역할별)
├── app/use_cases/region_industry_verdict_interactor.py
├── dependencies/region_industry_verdict_dependencies.py
├── domain/entities/region_industry_verdict_entity.py
└── domain/services/
    ├── thresholds.py    ← VerdictThresholds(on_percentile=0.75, strong_percentile=0.90), derive_levels()
    ├── signals.py       ← Signal(ABC).evaluate(...) → SignalResult ; 5개 구현 클래스 (Specification)
    └── rules.py         ← judge(results) → VerdictCode (Chain of Responsibility: Insufficient → Red → Orange → Clear)
```

`domain/`·`app/use_cases/`는 FastAPI·SQLAlchemy를 import하지 않는다.

### 4-2. 엔티티·DTO

```python
@dataclass(frozen=True)
class SignalResult:
    key: str                 # net_outflow | survival_cliff | early_closure | saturation | shrinking
    level: str               # off | on | strong | unavailable
    value: float | None      # 원값 (비율·개월·곳수). unavailable이면 None
    percentile: float | None # 나쁜 방향 백분위 0~100. 이진 신호·unavailable은 None
    evidence: str            # §3-4 문장
    source: str              # store | metric | neighborhood

@dataclass(frozen=True)
class RegionIndustryVerdict:
    region_code: str
    industry_id: str
    verdict_code: str        # red | orange | clear | insufficient
    strong_count: int
    on_count: int            # on + strong
    signals: tuple[SignalResult, ...]   # 항상 5개, §3-1 순서
    computed_at: datetime
```

### 4-3. 테이블 `region_industry_verdict` (마이그레이션 1개, down_revision `b7c8d9e0f1a2`)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| region_code | String(10) PK, FK region | |
| industry_id | String(40) PK, FK industry | |
| verdict_code | String(12) | red/orange/clear/insufficient |
| strong_count | SmallInteger | |
| on_count | SmallInteger | |
| signals_json | Text | `SignalResult` 5개 JSON 배열 |
| computed_at | DateTime(tz) | |

ERD 연결: region·industry에 FK. 1테이블 = 1프랙탈(§12). 역정규화 근거: `signals_json`은 카드가 통째로 읽고 질의 축이 아니므로 열 분해하지 않는다.

### 4-4. 배치 `build_verdicts`

1. 판정 대상 13업종 조회(IndustryCatalogPort).
2. StoreSignalStatsPort가 store 전량을 **한 번의 group_by(region_code, industry_id)** 로 세 집계를 반환: 12개월 개폐업·시작 점포수, 코호트 크기·생존 수, 최근 3년 폐업 영업개월 목록(중위값은 SQL `percentile_cont(0.5)`).
3. RegionContextPort가 동별 최신 연도 store_count(업종별)·최신 분기 resident_total·최신 분기 commerce_change(+서울 베이스라인)를 반환.
4. 업종별로 `derive_levels()`가 가드 통과 동의 분포에서 백분위·레벨을 매기고, `judge()`가 판정. 5,551행(13×427) 업서트, `computed_at = now`.
5. 실행 위치: `scripts/store-collector.sh`에서 `build_metrics` **바로 다음 줄**. 도커 8200 이미지는 결과 테이블만 읽는다(fp16 색인·지표와 같은 패턴).
6. 예상 시간: store 88만 행 group_by 3종 — 지표 집계(12초)와 같은 자릿수.

### 4-5. API

| 메서드·경로 | 응답 | 오류 |
|---|---|---|
| `GET /verdicts/myself` | 하드코딩 1행 왕복 — 배선 검증 먼저(§12 규칙) | |
| `GET /verdicts?industry=korean_food` | `list[{region_code, value: verdict_code}]` — 동네 유형 지표와 같은 **범주형 단계구분도 계약** | 404 `INDUSTRY_NOT_FOUND`(판정 대상 아님 포함) |
| `GET /verdicts/{region_code}?industry=korean_food` | `RegionIndustryVerdictResponse`(엔티티 전 필드, signals 5개) | 404 `INDUSTRY_NOT_FOUND` / `VERDICT_NOT_FOUND`(배치 전이거나 동 코드 오류) |

오류 바디는 `{error:{code,message}}`. `/{region_code}`는 `""`·`/myself` 뒤에 선언(neighborhood 라우터 주석과 동일한 함정).

## 5. 프론트 — 판정 카드·위험도 지도

### 5-1. 판정 카드 (`features/map-explorer/components/verdict-section.tsx`)

- 위치: 사이드패널 **헤더 직후, 동네 프로필 위**. `VerdictSection({regionCode, industry})`가 자기 훅 `useVerdict`(queryKey `["verdict", region, industry]`, `enabled: !!regionCode`)로 데이터를 가져와 업종 요약 로딩과 독립적으로 뜬다.
- 내용: 큰 판정 배지 4종(비추천·조건부·경고 없음·판정 보류) → 켜진 신호를 strong 먼저 나열(evidence 문장 + 원천 태그) → "근거 보기" 펼침에 5개 신호 전부(레벨·값·백분위·미판정 사유). 대안 두 축은 없음(2단계).
- 색은 토큰만: red `--danger`, orange `--warn`, clear `--text-secondary`, insufficient `--border`. 이모지는 배지에 넣지 않고 색·문구로 구분(스크린리더 고려, `aria-label`에 판정 문구).
- 404 `VERDICT_NOT_FOUND`(학원·어린이집·비노출 업종·배치 전)면 섹션을 그리지 않는다. 네트워크 오류는 한 줄 안내.
- 관문 → `/map?region&industry`이므로 이 카드가 첫 화면이 된다(§0-4). 관문 코드는 변경 없음.

### 5-2. 위험도 지도

- `map-state.ts` 업종 그룹에 범주형 지표 `verdict`(라벨 "창업 경고") 추가. 축은 새 값 **`industry_latest`** — 업종 select는 쓰고 연도 select는 숨긴다. `metricGroupOf().axis`로 분기하는 컨트롤바·`metric-coverage.ts`에 축 하나를 더 인식시키는 것이 전부.
- `shared/api/types.ts`: `CategoricalMetricKey = "neighborhood_type" | "verdict"`, `VerdictCode`, `VerdictSignal`, `RegionIndustryVerdict` 타입 추가. mock과 feature `api.ts`가 같은 타입을 import.
- `metric-sources.ts`: `verdictMetric()` 팩토리 1개 + `METRIC_SOURCES.verdict` 1줄. `fetchVerdictMetrics(industry)` → `GET /verdicts?industry=`.
- 색: `makeCategoryColorScale`로 4범주. 팔레트는 `lib/verdict-palette.ts`에 데이터 시각화 팔레트로 주석 선언(UI 토큰과 별개 체계, CLAUDE.md §16 예외). 범례는 기존 `CategoryRows`.
- 딥링크 `?metric=verdict&industry=korean_food`는 `parseMapState`가 그대로 받는다. `industry_latest` 축에서는 `year`를 직렬화하지 않는다.

## 6. 폐업 마커

### 6-1. 백엔드 (`store` BC, 계약 확장 — 기본값 불변)

- `GET /stores?region&industry&status=open|closed` — `status` 기본 `open`(현행과 동일 응답). `closed` = `close_date IS NOT NULL AND close_date >= today − 2y`, 좌표 보유.
- `StoreMarkerResponse`에 `close_date: date | None` 추가(open이면 null). 미지원 `status` 값은 422가 아니라 **404 `STORE_STATUS_NOT_FOUND`**(CLAUDE.md §15 "미지원 값은 500이 아니라 404"의 라우트 규칙을 그대로 따름).
- 포트: `StoreRepositoryPort.list_open(region, industry)` 유지 + `list_closed_since(region, industry, since: date)` 추가. 인터랙터 `list_stores(region, industry, status)`가 Strategy 맵으로 둘 중 하나를 고른다(if/else 금지). 엔티티 무변경.
- 응답 상한: 동×업종 2년 폐업이 수백 건이라 상한을 두지 않는다(강남 한식 2년 폐업 실측 후 1,000 초과 시 재검토).

### 6-2. 프론트

- 사이드패널 판정 카드 아래 토글 **"최근 2년 폐업 점포 보기"** (기본 꺼짐, URL·localStorage 미포함).
- `marker-strategies.ts`에 `CLOSED_STORE_STRATEGY`(queryKey `["stores-closed", region, industry]`, `fetchStores(region, industry, "closed")`, 팝업에 폐업일·영업 개월). 마커 색 `--danger`. 영업중 마커 위에 **추가**로 얹는다(대체 아님).
- 카드에 한 줄: "이 동에서 최근 2년 한식 N곳 폐업" — 토글 데이터의 length. 토글이 꺼져 있으면 문구도 없음(추가 요청 없음).
- 동 선택 시에만 로드하는 성능 가드 그대로.

## 7. 구현 순서 — 3단계, 단계마다 커밋·버전 로그

| 단계 | 내용 | 버전 | 완료 기준 |
|---|---|---|---|
| 1 | verdict BC: 도메인(신호·임계값·규칙) TDD → 게이트웨이 → 배치 → 마이그레이션 → 라우터(`/myself` 먼저) → `store-collector.sh` 한 줄 | BE v0.40.0 | 실DB 배치 1회, 13업종 판정 분포(red/orange/clear/insufficient 비율) 기록, `GET /verdicts?industry=korean_food` 427동 |
| 2 | 프론트 카드 + 지도: types → mock 라우트·픽스처·계약 테스트 → `metric-sources`·`map-state` 축 → `VerdictSection` → 범례 | FE v0.29.0 | Vitest 전부, 3200 실 API로 역삼1동 한식 카드 확인 |
| 3 | 폐업 마커: 백엔드 `status` + `close_date` → mock → `CLOSED_STORE_STRATEGY` + 토글 | BE v0.40.1 · FE v0.29.1 | 강남 한식 2년 폐업 마커 실표시, 건수 문구 |

각 단계 시작 전 `git status` 깨끗, 끝나면 `backend_ver_log.md`/`frontend_ver_log.md`.

## 8. 테스트

**백엔드**
- `tests/test_verdict_signals.py`: 신호별 값·가드(경계 9/10)·나쁜 방향 부호, 백분위 strict 계산, 75/90 경계, `shrinking` strong 조건.
- `tests/test_verdict_rules.py`: insufficient 우선(가능 2개+strong 2개 → insufficient), red/orange/clear 각 1건, 5개 signals 순서 고정.
- `tests/test_verdict_gateways.py`: `beyondfacade_test` DB에 store 행을 심어 12개월·코호트·중위개월이 SQL로 맞게 나오는지(폐업일 경계 포함).
- `tests/test_verdict_router.py`: `/verdicts/myself` 200 → 목록·상세·404 2종.
- 기존 542 passed 유지.

**프론트**
- mock 계약: `verdicts/route.test.ts`(200·INDUSTRY_NOT_FOUND), `verdicts/[regionCode]/route.test.ts`(VERDICT_NOT_FOUND), `stores/route.test.ts`에 `status` 기본값·closed·미지원 404.
- `verdict-section.test.tsx`: 판정 4종 렌더, strong 우선 정렬, 펼침, 404면 미렌더.
- `map-state.test.ts`·`metric-sources.test.ts`: `verdict` 축 `industry_latest`, year 미직렬화.
- `marker-strategies.test.ts`: closed 전략 queryKey·팝업 폐업일.
- 기존 326 passed 유지.

## 9. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| 양도·양수가 폐업+개업으로 잡혀 순유출·조기폐업이 부풀림(§0-10 라벨 오염) | 1단계 실DB 분포 기록 때 `early_closure` 중위값이 비정상(3개월 미만) 동을 표본 확인. 교차검증은 백테스트 단계 |
| 상권축소가 동 단위라 13업종에 동일하게 켜져 판정이 동 전체로 쏠림 | 신호 1개일 뿐이라 단독으로는 🟠까지. 근거 문장에 "동 전체 기준" 명시 |
| 백분위 상대평가는 항상 상위 25%를 켬 — 업종 전체가 좋아도 누군가는 🟠 | §0-8 결정 사항. 카드 문구를 "서울 같은 업종 중 상위 N%"로 써서 상대 기준임을 드러냄 |
| 표본 부족 동이 많으면 지도가 보류 색으로 덮임 | 1단계 분포 기록에서 insufficient 비율 확인, 30% 넘으면 가드 10 → 5 재검토(상수 한 곳) |
| 폐업 마커 수백 개 렌더 | 동 선택 시에만, 토글 기본 꺼짐. 1,000 초과 실측 시 상한 도입 |

## 10. 이 문서가 결정하지 않는 것

- 대안 두 축(동네 고정·업종 고정) — §0-7 2번, 별도 설계
- 백테스트·LightGBM 판정 전환 — §0-7 3번·§0-10
- 업종 특화 신호(담배권 원 등) — §0-7 4번
- 에이전트 리포트 verdict 섹션이 이 판정을 도구로 읽게 하는 것 — 후속(현재는 LLM 자유 서술)
- 서비스 이름·톤 — §0-8 팀 결정
- 저밀도 업종(당구장·PC방·중식·헬스장)의 높은 보류 비율 — 구(district) 단위 보완 집계는 후속

## 11. 진행 기록

| 일시 | 단계 | 결과 |
|---|---|---|
| 2026-09-29 | 1단계 완료 (BE v0.40.0) | 실DB 배치 1회 5,978행(14업종 × 427동), 소요 약 2.3초. 업종별 red/orange/clear/insufficient: cafe 35/255/130/7, hair_salon 26/237/152/12, korean_food 25/248/141/13, pub 22/182/130/93, pc_bang 14/104/34/275, western_food 11/150/59/207, chinese_food 10/110/32/275, karaoke 10/142/64/211, snack 9/202/104/112, billiard 7/66/12/342, japanese_food 4/148/74/201, gym 2/108/45/272, convenience_store 0/0/0/427, real_estate 0/234/183/10. insufficient 최대 비율은 convenience_store 100%(store 원천에 해당 업종 행이 아예 없음 — 표본 가드가 아니라 구조적 결측, §9 리스크 대응 대상 아님) 다음으로 billiard 80.1%. §9대로 `min_sample` 10→5 완화를 시도해 재실행했더니(billiard 45.4%·pc_bang 43.3%·gym 32.3%·karaoke 30.9%·chinese_food 30.9%로 개선) 기존 회귀 테스트 4건(`test_verdict_thresholds.py::test_기본_임계값_상수`, `test_verdict_signals.py`의 경계값 3건)이 상수 10을 고정 검증하고 있어 깨짐 — Task 7 범위 밖(다른 태스크의 테스트 파일)이라 되돌려 `min_sample=10`을 유지했다. 최종 커밋된 실DB 상태는 10 기준 분포. 표본 부족 완화는 후속 태스크에서 테스트까지 함께 다루는 것을 권장. |
| 2026-09-29 | Fix round 1 — 컨트롤러 Ruling A/B 반영 | **Ruling A(편의점 제외)**: `convenience_store`는 스냅샷 전용 원천이라 store 인허가 행이 없어 신호 3개가 영구 불가 — "표본 부족"이라 표시하면 근거가 틀린 문장이 되므로 `EXCLUDED_INDUSTRIES`에 추가해 판정 대상을 13업종으로 좁혔다(4단계 담배권 특화 신호 때 재포함). `test_verdict_thresholds.py::test_신호_키_순서와_제외_업종`(집합 5종)·`test_verdict_gateways.py::test_판정_대상_업종은_제외_5종을_뺀_13종`(len 13) 갱신, CLI·크론 문구의 "14업종"도 "13업종"으로 정정. 배치가 upsert-only라 기존 `convenience_store` 427행이 남아있어 `delete from region_industry_verdict where industry_id = 'convenience_store'`로 1회 정리(427행 삭제) 후 재실행 — 5,551행(13×427), 소요 약 2.2초. 나머지 13업종 분포는 사실상 동일(±1 수준의 미세한 차이는 `date.today()` 창이 9/28→9/29로 하루 밀린 데서 온 것으로, 코드 변경과 무관): cafe 36/252/132/7, hair_salon 26/236/153/12, korean_food 25/249/140/13, pub 22/182/130/93, pc_bang 14/104/34/275, western_food 11/151/58/207, chinese_food 10/110/32/275, karaoke 10/142/64/211, snack 9/200/106/112, billiard 7/66/12/342, japanese_food 3/153/70/201, gym 2/108/45/272, real_estate 0/234/183/10. **Ruling B(min_sample 10 유지)**: 5로 낮춰도 저밀도 업종은 여전히 30~45%가 보류이고 5건 표본의 백분위는 노이즈이므로, §3-3이 약속한 "정직한 보류"를 지키기 위해 임계값과 Task 3 회귀 테스트를 그대로 둔다. 전체 스위트 574 passed(변경된 테스트 포함) 재확인. |
| 2026-09-29 | 2단계 완료 (FE v0.29.0) | Task 8~11: 판정 타입·`shared/verdict.ts`(라벨·`isVerdictIndustry`) → mock `/verdicts`·`/verdicts/[regionCode]` + 결정적 픽스처 → 지도 `verdict` 범주 지표(축 `industry_latest`, 팔레트 `lib/verdict-palette.ts`) → 사이드패널 `VerdictSection`(자체 훅 `useVerdict`, 404는 섹션 없음, 배지 4색은 토큰, 켜진 신호 strong 먼저, "근거 보기"에 5개 전부). Task 11에서 브리프 스니펫 결함 2건을 고쳐 커밋: `verdict-section.tsx`에 빠진 `isVerdictIndustry` import 추가, 판정 보류 안내문이 배지 qualifier와 "표본 부족" 문자열을 중복시켜 테스트가 `getByText`로 유일 매치를 못 하던 것을 문구를 바꿔 해소. 내 `side-panel.tsx` 삽입이 `../api` 전체를 목으로 가는 기존 `side-panel.test.tsx`·`side-panel-period.test.tsx`의 `fetchVerdict` 부재를 깨뜨려 두 파일에 mock을 추가해 복구. 전체 스위트 **353/353 passed**, `tsc --noEmit` clean. 실 API 역삼1동 한식 `/verdicts` 응답 200 확인(3200 프록시). 카드 렌더는 브라우저 미확인 — 사용자 노트북에서 확인 필요. `/map` SSR grep은 무매치(페이지가 `Suspense fallback`만 SSR하고 지역·업종 의존 콘텐츠는 하이드레이션 후 클라이언트에서 채우는 기존 패턴 — §14, 회귀 아님). Fix round 1(리뷰 반영): 원천 태그(`SOURCE_LABEL` — 인허가·지표·상권분석) 표시 누락, `INDUSTRY_NOT_FOUND` 미테스트, 훅의 `retryDelay: 0`(프로덕션 코드 오염)을 테스트 `QueryClient` 기본값으로 이동, 검증 문구 과장 — 4건 모두 반영. |
| 2026-09-29 | 3단계 완료 (BE v0.40.1 · FE v0.29.1) | Task 12(BE): `GET /stores?status=open\|closed`(기본 open, 기존 응답 그대로) — closed는 최근 2년 폐업만, 마커 행에 `close_date` 추가(open은 null), 미지원 status는 404 `STORE_STATUS_NOT_FOUND`. 실측 역삼1동 한식 closed 300건. Task 13(FE): `Store.close_date`·`fetchStores(…, status)` → `CLOSED_STORE_STRATEGY`(queryKey `["stores-closed", region, industry]`, 팝업 개업일·폐업일·영업 개월, `--danger`) → `RegionMarkers`를 `strategy`·`sourceId`·`colorVar` props로 파라미터화(소스·레이어 id를 `sourceId`에서 파생)해 `MapView`에 두 번째 인스턴스(폐업 레이어)를 얹음 → `map-page.tsx`의 `showClosed` 상태(기본 꺼짐, URL·localStorage 미포함) → `SidePanel`의 `ClosedStoresToggle`(`VerdictSection` 바로 아래, 체크박스 + "이 동에서 최근 2년 {업종} N곳 폐업" — 같은 queryKey라 지도 레이어와 요청 1회로 합쳐짐). 브리프 스니펫 결함 2건을 고쳐 반영: (1) Step 1 테스트가 지정한 `region=1168052100&industry=cafe`는 표본상 cafe가 전 지역 `status_name: "영업"`뿐이라(폐업 표본 0건) `status=closed` 검증이 항상 빈 배열이 되는 구조적 불일치 — 동일 region의 `billiard`(폐업 표본 有, 전부 정확히 "폐업" 상태)로 교체, 나머지 단언은 그대로. (2) 건수 문구가 `<span className="tabular-nums">` 안에 숫자를 감싸 텍스트가 여러 노드로 쪼개져 RTL 기본 `findByText` 정규식이 못 찾음(RTL 문서에 명시된 알려진 제약) — `textContent` 함수 매처로 교체. 전체 스위트 **357/357 passed**, `tsc --noEmit` clean. 실 API 확인: `curl .../stores?region=1168064000&industry=korean_food&status=closed` → 300건, `close_date` 포함. 브라우저 화면(빨간 마커·건수 문구)은 미확인 — 사용자 노트북에서 확인 필요. |

## 12. 대안 두 축 (2026-09-29, HANDOFF §0-7 2번 · §0-8 "두 축 모두" 결정)

**입력은 `region_industry_verdict` 한 테이블 + 동네 유형 한 컬럼(`region_profile_quarter.neighborhood_type` 최신 분기). 신규 집계·배치 없음.**

- 동네 고정: 같은 동에서 판정 대상 13업종 중 자기 업종을 뺀 나머지.
- 업종 고정: 같은 업종에서 **동네 유형이 같은** 동 중 자기 동을 뺀 나머지. 동에 프로필이 없으면(유형 None) 빈 목록.

**순위 규칙 (domain/services/alternatives.py, 두 축 공통)**
- 후보는 `clear`·`orange`만 — `red`는 비추천이라 대안이 아니고 `insufficient`는 근거가 없다.
- 정렬 키 `(VERDICT_RANK[code], strong_count, on_count, id)`, `VERDICT_RANK = clear 0 · orange 1 · red 2 · insufficient 3`.
- **기준(현재 동×업종)보다 키가 작은 것만** 남긴다 → 기준이 `clear`면 대안 없음(카드에 안 그림), `insufficient`면 clear·orange 전부가 대안.
- 상위 3개(`ALTERNATIVE_LIMIT`).

**API** `GET /verdicts/{region_code}/alternatives?industry=` →
`{region_code, industry_id, neighborhood_type: str|null, industries: [{industry_id, industry_name, verdict_code, strong_count, on_count}], regions: [{region_code, region_name, verdict_code, strong_count, on_count}]}`.
404는 단건과 동일(`INDUSTRY_NOT_FOUND` / 기준 판정이 없으면 `VERDICT_NOT_FOUND`).

**프론트** — `VerdictSection` 아래 `VerdictAlternatives`(자체 훅 `useVerdictAlternatives`, queryKey `["verdict-alternatives", 동, 업종]`) 2줄:
"굳이 이 동네라면 ○○ · ○○ · ○○" / "굳이 {업종}이라면 ○○동 · ○○동 · ○○동 (같은 {유형} 동네 중)". 두 목록이 모두 비면 아무것도 그리지 않는다.
클릭해 지도 이동·업종 전환은 후속(관문→판정 착지와 같이).

## 13. 백테스트 한 장 (2026-09-29, HANDOFF §0-7 3번 · §0-5 · §0-10)

**질문**: 과거 시점 T의 데이터만으로 낸 판정이 그 뒤 실제 폐업을 가려냈는가.
"🔴 준 동×업종에서 T 직후 1년 안에 개업한 가게의 3년 내 폐업률 vs ⚪". 추천은 증명이 어렵지만 경고는 된다(§0-5).

**시점 T 재계산 — 누수 차단 (§0-10 "피처는 개업 시점 이전 값만")**
- store 집계: 기존 `signal_stats(today=T)` 그대로 — 창(12개월·코호트·3년)이 전부 T 기준 과거.
- 동 맥락: `latest_contexts(quarter_max)`·`latest_store_counts(year_max)`에 상한을 둔다. `quarter_max` = T가 속한 분기의 **직전 분기**(`quarter_before`), `year_max` = `T.year − 1`(점포수는 연말 스냅샷이라 T 이전에 확정된 마지막 연도).
  상한 None이면 현행 배치와 동일(최신). 판정 규칙·임계값은 그대로 — 백분위는 T 시점 분포에서 다시 나온다.
- 결과 라벨: T ≤ 개업일 < T+365일인 점포(진입 코호트)가 개업 후 1,095일 안에 폐업했는가(`EntrantOutcomePort`). 폐업일<개업일 오염 행은 제외.
  T + 365 + 1,095일 ≤ 오늘이어야 관측이 끝난다 → CLI가 검사. 기본 T = **2022-06-30**(프로필·변화지표가 2021Q1부터 있어 직전 분기 20221 존재).

**집계 (domain/services/backtest.py, 순수)**
- `(region, industry)`로 판정과 결과를 조인 → 판정 코드별 버킷 `{동×업종 조합 수, 개업 수, 3년 내 폐업 수}`. 전체와 업종별.
- 폐업률 = 폐업 ÷ 개업. lift = red 폐업률 ÷ clear 폐업률. 판정에 결과가 없는 조합(개업 0)은 조합 수에만 잡힌다.
- 이 단계에서는 규칙 판정만 검증한다. LightGBM(§0-10 ②) 도입은 이 표를 보고 결정 — 표에 lift가 없으면 규칙 신호 자체를 바꿔야 하지 모델을 얹을 일이 아니다.

**실행** `python -m apps.verdict.adapter.inbound.cli.backtest_verdicts --as-of 2022-06-30 [--out docs/verdict-backtest.md]` → 마크다운 표. 테이블·API 없음(발표용 한 장). 결과는 [`docs/verdict-backtest.md`](../../verdict-backtest.md).

**알려진 원천 한계**: 부동산은 진입 코호트 1,457곳 중 3년 내 폐업 0 — 원천(부동산중개업 인허가)에 폐업일이 사실상 없다. 표에 그대로 두되 해석에서 뺀다. 헬스장(448곳 중 39)도 같은 의심.

**결과 (2026-09-29, T=2022-06-30, BE v0.42.0)** — [`docs/verdict-backtest.md`](../../verdict-backtest.md)
- 전체: 🔴 58.3%(2,326곳) · 🟠 35.0%(14,043) · ⚪ 32.2%(4,188), lift 1.81×. **단 업종 구성 효과가 섞여 있다** — 🔴 개업 2,326곳 중 카페가 1,223.
- 업종별(정본): 카페 1.90×(74.3 vs 39.2%), 미용실 1.40×, 한식 1.15×. 중식·일식·양식·분식·호프·PC방은 1.0× 안팎 — 5개 공통 신호가 음식 업종에서는 동 간 폐업 차이를 못 가른다.
- 판단: 규칙 신호가 카페·미용실에서는 검증됐고 음식 업종에서는 아니다. LightGBM(§0-10 ②)을 얹기 전에 **신호별 lift**(어느 신호가 맞히는가)와 음식 업종용 피처(프랜차이즈 비중·시간대 불일치·임대료)를 먼저 봐야 한다 — 모델보다 피처 문제.
- 원천 한계 확인: 부동산 폐업률 0%(폐업일 없음), 헬스장 5~13%(의심). 두 업종의 생존·조기폐업 신호는 사실상 무의미 → 판정 대상 유지 여부를 팀이 결정.
- **신호별 lift (v0.43.0, 같은 T)**: 전체 생존 절벽 1.46× · 조기 폐업 1.32× · 순유출 1.28× · 포화 1.11× · 상권 축소 0.96×. store 원천 신호 3개는 작동하고, 동 단위 신호 2개(포화·상권 축소)는 카페를 빼면 거의 못 가른다 — 상권 축소는 전체에서 무신호(서울시 변화지표는 동 전체 기준이라 업종 폐업과 어긋난다). 한식은 5개 전부 1.0~1.24×라 규칙 신호로는 동 간 차이를 못 잡는다.
- **재실행 (2026-09-29, T=2022-06-30, BE v0.44.0, 부동산 제외 + 상권 축소 참고 신호화 후)**: 부동산 427개 동×업종이 표에서 사라지고 판정 대상 12업종. 전체 🔴 62.0%(1,951곳) · 🟠 38.4%(11,212) · ⚪ 36.9%(3,131), lift 1.68×(부동산의 0% 폐업이 빠지며 ⚪ 폐업률이 32.2%→36.9%로 올라 lift는 소폭 낮아졌다 — 원천 왜곡 제거가 원인, 신호 성능 저하가 아니다). 업종별: 카페 1.97×, 미용실 1.30×, 한식 1.18×. 상권 축소는 등급 계산에서 빠졌지만 신호별 lift는 여전히 0.96×(전체)로 참고 신호 판단이 맞았음을 재확인.
- **min_evaluable 3 → 2 재실행 (2026-09-29, T=2022-06-30, BE v0.44.0)**: 상권 축소를 참고 신호로 뺀 뒤에도 가드를 3으로 두니 판정 신호 4개 중 3개를 요구하게 되어 운영 보류가 **70.6%(5,124 중 3,618)**까지 올랐다. 2로 내린 뒤 운영 보류 **39.3%(5,124 중 2,014)**. 백테스트도 보류 3,640 → 1,920 동×업종으로 줄었고 전체 lift는 1.68× → **1.70×**(🔴 61.7%(1,960곳) · 🟠 37.7%(12,460) · ⚪ 36.2%(4,755)) — 가드를 풀어도 판별력은 떨어지지 않았다. 업종별: 카페 2.01×(1.97×), 미용실 1.41×(1.30×), 양식 1.10×(0.66×), 한식 1.16×(1.18×) — 보류에서 풀린 조합이 ⚪·🟠에 얹히며 표본이 두꺼워졌다.
