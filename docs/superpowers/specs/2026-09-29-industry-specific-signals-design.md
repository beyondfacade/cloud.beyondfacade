# 업종 특화 신호 — 편의점 담배권 이력 · 부동산 집계 판정 설계

> 작성 2026-09-29 · 백엔드 v0.45.0 / 프론트 v0.32.0 기준 · 브랜치 `feat/industry-specific-signals`
> 선행 문서: `docs/HANDOFF.md` §0-2(업종 특화 신호)·§0-7(실행 순서 4번)·§0-11(판정 대상)·§0-12 A, 판정 카드 설계서 `2026-09-28-verdict-card-design.md` §3·§4·§13, `docs/brainstorming.md` §3.5(담배소매인), `docs/verdict-backtest.md`
> 선례 코드: `apps/verdict/domain/services/signals.py`(Specification), `rules.py`(Chain of Responsibility), `adapter/outbound/gateways/store_signal_stats_gateway.py`(창 집계), `apps/convenience/domain/entities/convenience_store_entity.py`(브랜드 키워드 사전)

## 1. 목적

판정 대상에서 빠진 두 업종을 원천을 바꿔 다시 판정한다.

- **편의점**: store에 인허가 행이 없다(스냅샷 전용, 9/29 Ruling A). 폐업 이력은 **담배소매인 인허가**(`tobacco_retailer`)에 있다. 편의점 상호의 담배소매인을 편의점 개폐업의 대리 원천으로 삼아 공통 신호 5개를 그대로 돌리고, 편의점만의 **담배권 빈자리** 신호를 더한다.
- **부동산**: 개별 사무소의 폐업 이력이 어디에도 없다(브이월드·공공데이터·서울 열린데이터 모두 현행만). 대신 **서울시 상권분석 동×분기 집계**(`region_commerce_store`, CS200033)에 폐업 수가 있다. 이 집계로 신호 2개를 만들고 판정에 **"집계 기반"** 표시를 단다.

두 업종 모두 **백테스트 게이트를 통과해야** 판정 대상에 다시 들어간다(§8). 통과 못 하면 계산 경로는 남기고 제외 목록은 그대로 둔다.

부수 조사 3건: LOCALDATA 부동산중개업 원천 재확인(§12), 국토부 실거래가 파일럿(§11), 부동산 생존자 역산(§10).

## 2. 사전 조사 — 실DB 사실 (2026-09-29 조회)

### 2-1. 편의점 = 담배소매인 중 편의점 상호

| 항목 | 값 |
|---|---|
| `tobacco_retailer` 전체 | 95,402행 — 폐업처리 67,752 · 정상영업 15,615 · 지정취소 6,677 · 직권취소 5,240 · 임시소매기간만료 83 · 휴업 31 · 영업정지 4 |
| 날짜 | `permit_date` 전 행 채움(최솟값 1900-01-01 쓰레기값 존재), `designated_date` 72,466행 — **채워진 행은 전부 `permit_date`와 같다**. 폐업처리는 `close_date`, 지정·직권취소는 `cancel_date`에만 날짜가 있다 |
| 좌표·동 | `lat` 85,959 · `region_code` 85,948 (편의점 상호 행 중 동 미배정 983) |
| 원천 최신 날짜 | 2026-08-21 (정적 아카이브 2026-08-25 확보, 크론 비대상) |
| 편의점 상호 매칭(§5-1 사전) | 23,605행(1990년 이후 개업·동 배정분). 옛 이름 기여: 훼미리마트 1,684 · 코리아세븐 1,494 · 바이더웨이 465 · LG25 418 · 위드미 330 · 엘지25 41 |
| 'CU' 경계 매칭 | `(?<![A-Z])CU(?![A-Z])` 1,131행 — 표본 25건 전부 실제 CU 점포. `GS리테일`·`지에스리테일` 67행은 GS수퍼마켓이 섞여 사전에서 뺀다 |
| 양도·양수 노이즈 | 편의점 폐업 15,573건 중 **2,482건(16%)** 이 같은 지번주소에서 ±90일 안에 새 편의점 담배소매인 지정과 짝을 이룬다 |
| 승계 접기 후 | 에피소드 20,884개(접힌 것 2,136). 현재 영업 7,634 (스냅샷 `convenience_store` 9,395의 81%) |
| 표본 가드 통과 동(오늘 기준) | 12개월 전 영업 ≥ 10: **333/427** · 3~4년 전 개업 코호트 ≥ 10: **2/427** · 최근 3년 폐업 ≥ 10: **40/427** |
| 백테스트 진입 코호트 (T=2022-06-30) | 1년 안 개업 779곳, 그중 3년 내 폐업 115곳(14.8%) |

→ 편의점 판정은 사실상 **순유출·포화 두 신호**로 내려진다. 생존 절벽·조기 폐업은 동 단위 표본이 안 되어 대부분 `unavailable` — 정직한 결과이고 가드를 낮추지 않는다(판정 카드 설계서 §11 Ruling B와 같은 이유).

### 2-2. 담배소매인 간격 (정상영업 15,199곳, 좌표 보유)

| 항목 | 값 |
|---|---|
| 가장 가까운 다른 소매인까지 거리 | p5 0m · p10 0m · p25 46m · **중위 71m** |
| 50m 안에 다른 소매인이 있는 비율 | 28% (대부분 0m — 같은 건물·같은 좌표, 대형 건물 예외로 추정) |
| 100m 안에 다른 소매인이 있는 비율 | **73%** (구별 62~95%) — 100m 제한을 전면 적용하는 구는 없다 |
| 영업 중 상가(store 255,585곳) 중 소매인 50m 안 비율 | 동별 p10 0.50 · 중위 0.65 · p90 0.76 |
| 같은 지표를 100m로 | 동별 p10 0.83 · 중위 **0.95** · p90 0.99 — 거의 전부 막혀 동 간 차이가 사라진다 |

### 2-3. 부동산 = 상권분석 집계 CS200033

| 항목 | 값 |
|---|---|
| 범위 | 20211~20254, 8,484행, 422동 (동 미배정 60행, 한 동에 상권코드 둘 이상인 동×분기 20건) |
| 동 점포수 분포(20221) | p10 35 · 중위 75 · p90 180 |
| **연도별 개업 수** | 2021 5,269 · 2022 4,501 · 2023 4,307 · **2024 222 · 2025 150** |
| 연도별 폐업 수 | 2021 3,572 · 2022 3,383 · 2023 4,288 · 2024 3,817 · 2025 2,985 |
| 스냅샷(store) 등록일 연도별 | 2023 1,525 · 2024 1,559 · 2025 1,941 — 실제 개업은 줄지 않았다 |
| 분기 폐업률(2025, 동별) | p10 0.65% · 중위 1.84% · p90 3.27% |
| 점포수 순위 일치 | 아카이브 20254 점포수 vs 스냅샷 영업 사무소 수 Spearman **ρ = 0.946** (421동) |

→ **아카이브의 부동산 개업 수는 2024년 1분기부터 사실상 0**이다(원천 쪽 수집 단절로 보인다). 폐업 수와 점포수는 연속적이고 스냅샷과 순위가 맞는다. 그래서 부동산 신호는 **순유출(폐업 − 개업)이 아니라 폐업률**로 만든다(§7).

### 2-4. 부동산 스냅샷 (store `real_estate`)

영업중 25,207 · 폐업(추정) 157(9/7~9/29 스냅샷 소실) · 휴업 59 · 업무정지 22 · 휴업연장 4. `open_date`(등록일)는 전 행 있다.

## 3. 결정 사항

| 항목 | 결정 | 이유 |
|---|---|---|
| 원천 교체 방식 | **업종별 원천 Strategy** — 도메인 `SignalProfile`(어떤 신호를 어떤 표기로) + 출력 포트 `IndustrySignalDataPort`(집계·점포수·진입 결과) 한 쌍을 업종 id로 등록. 등록 안 된 업종은 기존 인허가 원천 | 인터랙터에 `if industry == ...`를 넣지 않는다(CLAUDE.md §5). 새 원천은 등록 한 줄 |
| 편의점 개폐업 | 담배소매인 중 **브랜드 사전(옛 이름 포함)** 매칭 행 → 같은 지번 ±90일 **승계 접기** → 에피소드 단위로 기존 창 집계와 같은 규칙 | 양도·양수 16%를 폐업+개업으로 세면 순유출·조기 폐업이 부풀어 오른다 |
| 브랜드 없는 개인 편의점 | **넣지 않는다** — 스냅샷 좌표 매칭 보강 안 함 | 판정 대상을 스냅샷과 같은 "체인 편의점"(`convenience_store` 원천 G20405)으로 맞춘다. '기타' 74k는 슈퍼·담배가게가 섞여 이력 오염이 크다. 좌표 매칭은 현재 영업 점포만 잡혀 과거 폐업을 못 살린다 |
| 편의점 분석 기준일 | `min(오늘, 원천 최신 날짜)` | 정적 아카이브(8/21)를 오늘(9/29) 창으로 세면 마지막 한 달이 비어 개폐업이 과소 집계된다 |
| 담배권 빈자리 | 편의점 전용 **참고 신호** `tobacco_gap` (등급 계산 제외) | 폐업 위험이 아니라 **진입 가능성**을 재는 신호다. 판정 등급은 폐업 대조로 검증되는 값이라 섞으면 🔴의 뜻이 둘이 된다. 백테스트 신호별 lift는 기록한다 |
| 빈자리 반경 | **50m**, 도메인 상수 `TOBACCO_GAP_RADIUS_M` | 소매인 간격 분포(§2-2): 100m 안 이웃 73%라 100m 제한 구는 드물고, 100m로 재면 동 중위 95%가 막혀 변별력이 없다. 구별 조례 반영은 후속 |
| 부동산 신호 | **폐업률**(`closure_rate`, 신규) + **포화**(아카이브 점포수) — 등급 신호 2개. 생존 절벽·조기 폐업은 "산출하지 않음"(Null Object) | 아카이브 개업 수가 2024Q1부터 0이라 순유출은 거짓 문장이 된다(§2-3). 개별 점포 날짜가 없어 코호트 신호는 원천상 불가 |
| 판정 원천 표시 | `region_industry_verdict.basis` 컬럼 신설 — `permit`(인허가 개별 이력) · `proxy`(담배소매인 대리 이력) · `aggregate`(동×분기 집계). API 응답에도 싣는다 | 카드가 "집계 기반 판정" 배지를 달 근거. 신호별 `source`와 별개로 판정 한 행의 성격 |
| 재포함 게이트 | **경고(🔴+🟠) 폐업률 ÷ ⚪ 폐업률 ≥ 1.10×** + 표본 하한 (§8) | 🔴는 등급 신호 2개가 둘 다 strong이어야 나와 몇 개 동뿐이다 — 🔴/⚪는 수십 곳 개업으로 갈린다 |
| 부동산 백테스트 | 동 단위: T 분기 점포수 대비 이후 12분기 폐업 수(§7-3) | 개별 개업일이 없어 진입 코호트를 만들 수 없다 |
| 국토부 실거래가 | 파일럿 호출 200일 때만 진행, **참고 신호**로만 | 활용신청 여부 미확인. 법정동 → 행정동 배분이 근사라 등급 신호로 쓰기 전 lift 확인이 필요 |

## 4. 구조 — 업종별 원천 Strategy

```
IndustryCatalog ─ judged_industries() ─┐
                                        ▼
RegionIndustryVerdictInteractor.compute(today, quarter_max, year_max, industries)
   for industry: source = sources.get(industry_id, default)      ← 레지스트리 조회(dict), 분기 없음
                 stats  = source.data.signal_stats(today)          ← 원천마다 1회(캐시)
                 counts = source.data.store_counts(year_max, quarter_max)
                 signals = source.profile.signals()                ← 도메인 Strategy
                 → SignalInput → evaluate → judge → RegionIndustryVerdict(basis=source.profile.basis)
```

| 계층 | 파일 | 역할 |
|---|---|---|
| domain | `services/profiles.py` | `SignalProfile(ABC)`: `basis`, `signals()`. `PermitProfile` · `TobaccoProxyProfile` · `AggregateProfile` |
| domain | `services/signals.py` (추가) | `SourcedSignal`(Decorator — 같은 계산, source 표기만 교체) · `UnsupportedSignal`(Null Object — 원천이 재료를 안 줌) · `ClosureRateSignal` · `TobaccoGapSignal` |
| domain | `services/convenience_history.py` | 브랜드 사전·`brand_of`·`RetailerRecord`·`Episode`·`fold_successions` |
| domain | `services/tobacco_gap.py` | `TOBACCO_GAP_RADIUS_M`·`GeoPoint`·`blocked_counts`(격자 근접 판정) |
| app | `ports/output/region_industry_verdict_port.py` (추가) | `IndustrySignalDataPort`: `signal_stats(today)`·`store_counts(year_max, quarter_max)`·`entrant_outcomes(as_of, entry_days, horizon_days)` / `IndustryCatalogPort.named_industries(ids)` |
| app | `use_cases/industry_source.py` | `IndustrySource(profile, data)` · `PermitSignalData`(기존 포트 3개를 묶는 Adapter) |
| adapter | `gateways/tobacco_convenience_gateway.py` | `TobaccoConvenienceSignalData` — tobacco + store(상가 좌표) ORM |
| adapter | `gateways/commerce_aggregate_gateway.py` | `CommerceAggregateSignalData` — region_commerce_store + industry_source_code ORM |
| composition | `dependencies/…` | `sources={"convenience_store": IndustrySource(TobaccoProxyProfile(), TobaccoConvenienceSignalData()), "real_estate": IndustrySource(AggregateProfile(), CommerceAggregateSignalData(("real_estate",)))}` |

`IndustrySignalDataPort`는 메서드 3개지만 역할은 하나("한 업종군의 개폐업 원천")다. 원천을 바꾸면 세 메서드가 같이 바뀌므로 ISP상 한 포트로 둔다.

원천 등록과 판정 대상은 별개다. 레지스트리에 있어도 `EXCLUDED_INDUSTRIES`에 있으면 배치·API는 판정하지 않고, 백테스트 `--candidates`로만 돈다.

## 5. 편의점 (A)

### 5-1. 브랜드 사전 (도메인 상수, 순서 있는 튜플 — 첫 일치가 이긴다)

| 브랜드 | 패턴(대문자화한 상호에 `re.search`) | 비고 |
|---|---|---|
| GS25 | `GS\s*25` · `지에스\s*25` · `LG\s*25` · `엘지\s*25` | LG25 → GS25(2005) |
| CU | `(?<![A-Z])CU(?![A-Z])` · `씨유` · `훼미리\s*마트` · `패밀리\s*마트` · `FAMILY\s*MART` · `비지에프` | 훼미리마트 → CU(2012). 'CU'는 영문자 경계 필수(CUBE·SCU 오탐 방지) |
| 세븐일레븐 | `세븐\s*-?\s*일레븐` · `7\s*-?\s*ELEVEN` · `(?<!\d)7-11(?!\d)` · `바이더웨이` · `BUY\s*THE\s*WAY` · `코리아세븐` | 바이더웨이 합병. 맨 `세븐`은 넣지 않는다(세븐마트 등) |
| 이마트24 | `이마트\s*24` · `EMART\s*24` · `위드미` · `WITH\s*ME` | 위드미 → 이마트24(2017) |
| 미니스톱 | `미니스톱` · `MINI\s*STOP` | |
| 기타 체인 | `365\s*플러스` · `홈플러스\s*365` · `스토리웨이` · `씨스페이스` · `C-?\s*SPACE` · `로그인\s*25` | 맨 `로그인`은 넣지 않는다 |

사전은 verdict 도메인에 둔다. convenience BC의 `extract_brand`(스냅샷 표시용, 옛 이름 없음)는 건드리지 않는다 — 목적이 다르다(표시 vs 과거 이력 복원).

### 5-2. 레코드 → 에피소드

- 레코드: `open_date = designated_date or permit_date`, `close_date = close_date or cancel_date`, `address_key = 지번주소 공백 정규화`. `region_code` 없거나 `open_date < 1990-01-01`이면 버린다.
- **승계 접기** (`fold_successions`, 기본 90일): 같은 `address_key` 안에서 개업일 순으로 보며, 새 레코드의 개업일이 **이미 닫힌 에피소드의 폐업일 ±90일 안**이면 그 에피소드에 잇는다(가장 가까운 것 하나). 이은 에피소드의 폐업일 = 새 레코드 폐업일(없으면 영업 중, 있으면 두 폐업일 중 늦은 쪽). 영업 중인 에피소드와 같은 주소에 새 레코드가 오면 **잇지 않는다** — 대형 건물 안 동시 영업 점포를 합치지 않기 위해. 주소가 없는 레코드는 자기 혼자 에피소드.
- 에피소드는 "그 자리의 편의점"이다. 브랜드가 바뀌어도(GS25 → CU) 편의점 업종으로는 폐업이 아니다.

### 5-3. 창 집계 — 인허가 원천과 같은 규칙

`stats_from_episodes(episodes, today)`는 `StoreSignalStatsGateway`의 SQL과 한 줄씩 대응한다(12개월 전 영업·12개월 개폐업·[today−4y, today−3y) 코호트·3년 생존·최근 3년 폐업의 영업개월 중위값, 폐업일 < 개업일 행은 조기 폐업에서 제외). `today`는 `min(요청일, 원천 최신 날짜)`.

- 점포수(포화 분모 대비 분자): 기준일에 영업 중인 에피소드 수. 배치는 원천 최신 날짜, 백테스트는 `year_max`년 12월 31일.
- 진입 결과: `[as_of, as_of+365)` 개업 에피소드 중 개업 후 1,095일 안 폐업(판정 카드 설계서 §13과 같은 라벨).
- 표기: 순유출·생존 절벽·조기 폐업·포화의 `source`는 `tobacco`(카드 태그 "담배소매인"). 상권 축소는 `neighborhood` 그대로.

### 5-4. 한계

- 원천이 정적 아카이브라 편의점 판정은 **2026-08-21 시점**에 멈춘다. 파일 재확보 → `load_tobacco_retailer` 재실행이 갱신 절차(크론 비대상). 판정 행의 `computed_at`은 배치일이라 기준일과 다르다 — 카드 배지 툴팁에 원천 기준을 적는다.
- 체인 편의점만 센다. 개인 편의점이 많은 동은 과소 집계된다.

## 6. 담배권 빈자리 (B)

### 6-1. 정의

동 d, 기준일 D:
- **후보 자리** = store에서 D에 영업 중(`open_date ≤ D`, `close_date` 없음 또는 `> D`)이고 좌표·동이 있는 상가 전부(업종 무관).
- **막힌 자리** = 후보 자리 중 D에 영업 중인 담배소매인(편의점 여부 무관, `open ≤ D`, 폐업·취소일 없음 또는 `> D`, 상태 '임시소매기간만료' 제외, 좌표 보유)이 **50m 안**에 하나라도 있는 자리.
- 값 `tobacco_gap = 막힌 자리 ÷ 후보 자리`. 높을수록 나쁨. 가드: 후보 자리 < 30이면 `unavailable`(`VerdictThresholds.min_gap_candidates = 30` — 비율 표본이라 점포 가드 10보다 크게).
- 레벨: 다른 신호와 같이 편의점 427동 안 백분위 75/90. 근거 문장은 절대값을 말한다: "이 동 상가 자리 1,234곳 중 71%가 영업 중인 담배소매인 50m 안 — 새 담배소매인 지정이 어렵다 (서울 상위 12%)".
- 거리는 서울 위도(37.55°) 기준 등장방형 근사, 격자 한 칸 = 반경. 실측 계산 4초(상가 25만 × 소매인 1.5만).

### 6-2. 참고 신호인 이유

`ADVISORY_SIGNAL_KEYS`에 넣는다 → 평가·저장·카드 "참고" 줄 표시, 등급 계산 제외. 판정 등급은 "여기서 열면 문 닫는가"를 백테스트로 검증한 값이고, 빈자리는 "여기서 담배권을 받을 수 있는가"를 잰다. 백테스트 신호별 lift 표에 칸을 두어 폐업과의 관계는 기록한다. 등급 신호 승격은 lift ≥ 1.10이 나오고 팀이 결정할 때만.

## 7. 부동산 (E)

### 7-1. 신호 (`AggregateProfile`, 표시 순서)

| key | 이름 | 값 | 등급 | source |
|---|---|---|---|---|
| `closure_rate` | 폐업률 | 최근 4분기 폐업 수 합 ÷ 4분기 전 점포수 | 등급 | `commerce` |
| `survival_cliff` | 생존 절벽 | — (`UnsupportedSignal`: "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음") | — | `commerce` |
| `early_closure` | 조기 폐업 | — (같은 사유) | — | `commerce` |
| `saturation` | 포화 | 아카이브 점포수 ÷ (상주인구/1,000) | 등급 | `commerce` |
| `shrinking` | 상권 축소 | 기존 그대로 | 참고 | `neighborhood` |

- 분기 창: `q_last` = 아카이브에 있는 분기 중 `quarter_before(today)` 이하의 최신(배치 20254, T=2022-06-30이면 20221). `q0 = q_last − 4분기`. 시작 점포 = `q0` 점포수 합, 폐업 = (`q0`, `q_last`] 폐업 수 합. 한 동에 상권코드가 여럿이면 합한다.
- 점포수: 배치는 아카이브 최신 분기, 백테스트는 `quarter_max` 이하 최신 분기. (2024년 이후 점포수에는 신규 개업이 빠져 있지만 스냅샷과 순위 ρ 0.946 — 상대평가에는 쓸 만하다.)
- 판정: 등급 신호가 2개뿐이라 `min_evaluable = 2`는 **둘 다** 계산돼야 판정. 🔴 = 둘 다 strong.
- 폐업률 근거 문장: "지난 4분기 폐업 18곳 (4분기 전 점포 1,251곳의 1%, 서울 부동산중개업 상위 30%, 서울시 상권분석 집계)".

### 7-2. "집계 기반" 표시

판정 행 `basis = "aggregate"` → API `basis` → 카드 배지 "집계 기반 판정"(툴팁: "개별 점포의 개업·폐업일이 아니라 서울시 상권분석 동×분기 집계로 판정 — 생존 절벽·조기 폐업은 산출하지 않습니다"). 편의점은 `basis = "proxy"` → 배지 "담배소매인 이력 기준"(툴팁: "편의점 개폐업을 담배소매인 지정·폐업 이력으로 대신 셉니다 — 원천 기준 2026-08"). 인허가 업종은 배지 없음.

### 7-3. 동 단위 백테스트

진입 코호트 대신 **재고 결과**: `EntrantOutcome(opened = T가 속한 분기 점포수, closed_within = 그다음 분기부터 T+horizon이 속한 분기까지 폐업 수 합)`. T=2022-06-30이면 노출 20222, 폐업 20223~20252(12분기). 폐업률 = 폐업 ÷ 노출.
단위가 달라 **"전체" 합산 버킷에서는 빼고** 업종 행에만 둔다(표에 † 표시). 신호 창(≤20221)과 결과 창(≥20223)이 겹치지 않아 누수 없음.

## 8. 재포함 게이트

**질문**: 새 원천으로 낸 판정이 기존에 "작동한다"고 본 업종만큼 폐업을 가르는가.

| 항목 | 기준 |
|---|---|
| 지표 | **경고 lift** = (🔴+🟠 폐업 합 ÷ 🔴+🟠 개업 합) ÷ (⚪ 폐업 ÷ ⚪ 개업) |
| 통과선 | **≥ 1.10×** |
| 표본 — 대리 원천(편의점) | 경고·⚪ 각각 개업 ≥ 50곳 |
| 표본 — 집계 원천(부동산) | 경고·⚪ 각각 동 ≥ 30곳 |
| 시점 | T = 2022-06-30 (판정 카드 백테스트와 같음) |

**1.10의 근거** — 지금 판정 대상 12업종의 같은 지표(`docs/verdict-backtest.md` 9/29 표에서 계산): 카페 **1.36** · 미용실 **1.16** vs 한식 1.00 · 양식 0.92 · 일식 0.93 · 호프 0.96 · 분식 1.07 · PC방 1.08 · 중식 0.81. 신호가 작동한다고 판단한 두 업종과 못 가른다고 판단한 나머지 사이가 1.08~1.16이다. 새 원천은 "작동하는 쪽"임을 보여야 한다.
기존 약한 업종(한식 등)이 이 선을 못 넘는데도 판정 대상인 비대칭은 알고 둔다 — 그 업종들은 원천이 검증된 인허가이고 신호 쪽이 약한 것(HANDOFF §0-12 A 후속)이며, 여기서는 **원천 자체가 새것**이라 먼저 증명을 요구한다.

**🔴/⚪가 아닌 이유** — 두 업종 모두 등급 신호가 사실상 2개(§2-1·§7-1)라 🔴는 두 신호가 모두 90백분위 이상인 몇 개 동뿐이다. 편의점 진입 코호트 779곳 중 🔴에 들어갈 개업은 수십 곳 이하로 예상돼 비율이 우연에 흔들린다.

**표본 하한의 근거** — 편의점 3년 폐업률 약 15%에서 50곳이면 표준오차 약 5%p. 게이트를 확정하기엔 넉넉하지 않지만 이보다 작으면 lift 계산 자체를 믿을 수 없다. 부동산은 결과 단위가 동이라 동 수로 센다(30).

게이트 결과는 `backtest_verdicts --candidates` 표의 "게이트" 칸에 자동으로 찍힌다(`reinclusion_gate`, 도메인 순수 함수). 통과 → `EXCLUDED_INDUSTRIES`·프론트 `VERDICT_EXCLUDED_INDUSTRIES`에서 뺀다. 미달 → 그대로 두고 결과를 이 문서 §17과 HANDOFF에 적는다.

## 9. 계약 변경

### 9-1. 테이블 (마이그레이션 1개, down_revision `c9d0e1f2a3b4`)

`region_industry_verdict.basis String(12) NOT NULL server_default 'permit'`. 기존 행은 전부 인허가 원천이라 기본값이 곧 참값이다. 역정규화 아님(판정 행 자신의 속성).

### 9-2. 엔티티·신호 키

- `RegionIndustryVerdict.basis: str = "permit"`(마지막 필드, 기본값 — 기존 생성자 호환).
- `SIGNAL_KEYS`(공통 5개)는 그대로. `SPECIFIC_SIGNAL_KEYS = ("closure_rate", "tobacco_gap")`, `ALL_SIGNAL_KEYS = SIGNAL_KEYS + SPECIFIC_SIGNAL_KEYS`(백테스트 정렬·표 칸). 실거래가를 붙이면(§11) `"trade_per_office"`를 덧붙인다.
- `ADVISORY_SIGNAL_KEYS = {"shrinking", "tobacco_gap"}`(+ `"trade_per_office"`).
- `signals`는 "항상 5개"가 아니라 **프로필이 정한 개수·순서**다: 인허가 5 · 편의점 6 · 부동산 5.

### 9-3. API

`GET /verdicts/{region}?industry=` 응답에 `basis: "permit" | "proxy" | "aggregate"` 추가. `signals[].key`에 `closure_rate`·`tobacco_gap`, `signals[].source`에 `tobacco`·`commerce`가 새로 올 수 있다. 목록 `GET /verdicts?industry=`는 불변. 404 규칙 불변(제외 업종은 `INDUSTRY_NOT_FOUND`).

## 10. 부동산 생존자 역산 (F) — 분석만

현재 영업 사무소(스냅샷)의 등록 연도별 수 ÷ 아카이브 같은 연도 개업 수 합(2021~2025). 동 단위로는 2021~2023 합산 비율의 분포(p10·중위·p90, 비율 > 1인 동 수).
읽는 법: 비율 ≈ 그 연도 개업의 현재까지 생존율 × (스냅샷 포착률 ÷ 아카이브 포착률). 2024~2025는 아카이브 개업이 0에 가까워 비율이 발산할 것 — 그 자체가 §2-3 단절의 확인이다.
결과는 §17과 HANDOFF에 적고, 신호 채택은 결과를 보고 따로 판단한다(이 계획에서 신호로 만들지 않음). CLI `real_estate_survivor_backcast`.

## 11. 국토부 실거래가 (G) — 파일럿 게이트

1. **파일럿**: `DATA_GO_KR_API_KEY`로 `apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade`(아파트 매매) · `RTMSDataSvcAptRent/getRTMSDataSvcAptRent`(아파트 전월세) · `RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade`(상업업무용 매매, 활용신청 기록 있음)를 `LAWD_CD=11680&DEAL_YMD=202406` 1회씩 호출. HTTP 상태·`resultCode`·`totalCount`를 `docs/api.md`에 기록.
2. **아파트 매매가 200 + 정상 코드가 아니면 중단** — HANDOFF에 "외부 대기(활용신청)"로 적고 이 절 나머지는 하지 않는다.
3. 진행 시 범위(최소): 아파트 매매 **건수만**, 구×법정동×월(2021-01~). 신규 보조 테이블 `apt_trade_count`(district FK — tobacco·rent와 같은 "수집 전용 보조 테이블", 라우터 없음). 법정동 → 행정동은 store 지번주소의 (구, 법정동)별 행정동 분포 비율로 배분(근사). 신호 `trade_per_office` = 최근 12개월(기준월 2개월 전까지 — 신고기한 30일) 배분 거래 수 ÷ 아카이브 점포수, 낮을수록 나쁨, **참고 신호**. 백테스트 신호별 lift로만 평가.

## 12. LOCALDATA 부동산중개업 재확인 (I) — 조사만

기획서(`brainstorming.md:196`)는 LOCALDATA에 부동산중개업 개폐업 일자가 있다고 적었고, `api.md:188`(8/25)은 행안부 통합 목록에서 미확인이라 적었다. 둘 중 무엇이 맞는지 행안부 인허가 목록(data.go.kr 국가중점데이터 1741000)·localdata.go.kr 파일 다운로드 목록·서울 열린데이터 "부동산 중개업" 데이터셋 컬럼을 다시 확인한다. 폐업일 있는 원천이 있으면 **후속 과제로만 기록**(이 계획에서 수집기를 만들지 않음) — 그 원천이 생기면 부동산은 `permit` 원천으로 옮겨 코호트 신호까지 살린다.

## 13. 프론트 (구현: Codex)

- 타입: `VerdictBasis`, `RegionIndustryVerdict.basis`, `VerdictSignalKey`에 `closure_rate`·`tobacco_gap`(+G), `VerdictSignal.source`에 `tobacco`·`commerce`. mock 픽스처가 업종별 basis·신호 목록을 백엔드 프로필대로 미러.
- `shared/verdict.ts`: 신호 라벨(폐업률·담배권 빈자리), `ADVISORY_SIGNAL_KEYS`에 `tobacco_gap`, 배지 문구·툴팁 테이블, 제외 업종 안내 문구 테이블, 게이트 결과에 따른 `VERDICT_EXCLUDED_INDUSTRIES`.
- `VerdictCard`: basis 배지(permit은 없음), 원천 태그 2종 추가, 참고 신호가 둘 이상이면 전부 "참고:" 줄로.
- brief: 판정 제외 업종이면 `VerdictSection`이 카드 대신 **안내 한 줄** "판정 준비 중인 업종 — {사유}". 사이드패널의 편의점 전용 분기(`industry === "convenience_store"`)를 **업종별 추가 섹션 레지스트리**로 바꾸고 "판정은 담배권 특화 신호 단계에서 제공" 하드코딩 문구를 없앤다.
- 계약 테스트: 단건 응답 `basis`, 편의점·부동산 단건(재포함 시 200 + 신호 목록, 미달 시 404 `INDUSTRY_NOT_FOUND`).

## 14. 테스트

**백엔드** (현행 694 collected 유지 + 신규)
- `test_verdict_convenience_history.py`: 브랜드 사전(옛 이름·CU 경계·수퍼 제외), 승계 접기 5경우, `blocked_counts` 반경 경계(40m 막힘·60m 열림).
- `test_verdict_profiles.py`: 프로필별 키 순서·basis·source 교체·Null Object 사유·폐업률·빈자리 값과 가드·참고 신호는 등급 제외.
- `test_verdict_sources.py`: 인터랙터가 업종별 원천을 쓰고(기본 원천 행 무시), basis를 싣고, 원천별 1회 조회, 집계 원천은 전체 합산에서 빠진다.
- `test_verdict_tobacco_source.py`: 창 집계 순수 함수(인허가 SQL과 같은 기대값), DB 게이트웨이(승계 접기·기준일 고정·빈자리·점포수·진입 결과).
- `test_verdict_commerce_source.py`: 분기 창·동 합산·점포수 상한·재고 결과.
- `test_verdict_backtest.py`: 분기 보조 함수, 게이트 통과·lift 미달·표본 미달. `test_verdict_backtest_cli.py`: 심사 절 렌더.
- 기존 fake 카탈로그 3곳에 `named_industries` 추가.

**프론트** — mock 계약(`basis`·신호 키), `verdict-card`(배지 3종·참고 여러 줄·원천 태그), `verdict-section`(제외 업종 안내), `side-panel`(레지스트리).

## 15. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| 편의점 판정이 순유출·포화 2신호에 의존 | 게이트가 이 상태 그대로의 판정을 검증한다. 가드 완화는 하지 않는다 |
| 브랜드 사전 누락·오탐 | Task 12에서 에피소드 폐업 수(동×연)와 상권분석 CS300002 폐업 수의 순위 상관을 재서 기록. ρ < 0.6이면 사전 재검토를 후속으로 |
| 승계 접기가 동시 영업 점포를 합침 | 영업 중 에피소드에는 잇지 않는다(§5-2). 테스트로 고정 |
| 부동산 아카이브 개업 단절이 폐업 쪽으로 번짐 | 폐업 수는 2024~2025에도 연속(§2-3). Task 12에서 최신 4분기 폐업 합이 0인 동 비율을 재서 기록 — 30% 넘으면 원천 점검 후속 |
| 편의점 원천 정적(2026-08) | 배지 툴팁에 기준 명시, HANDOFF에 갱신 절차 |
| 빈자리 50m가 일부 구 조례와 다름 | 상수 한 곳. 구별 조례 조사 → 구별 반경은 후속 |
| 대안 목록에 집계 기반 판정이 섞임 | 대안은 판정 코드만 비교하므로 동작은 맞다. 표시상 구분은 후속 |

## 16. 이 문서가 결정하지 않는 것

- 담배권 빈자리의 등급 신호 승격(lift 확인 후 팀 결정)
- 구별 담배소매인 거리 조례 반영
- 편의점 담배소매인 아카이브 자동 갱신(크론화)
- 실거래가를 등급 신호로 쓰는 것, 전월세·상업용 거래 추가
- 생존자 역산의 신호 채택
- LOCALDATA에 폐업일 원천이 있을 때의 수집기
- 기존 약한 업종(음식 5종 등)의 판정 대상 재검토

## 17. 진행 기록

| 일시 | 단계 | 결과 |
|---|---|---|
| 2026-09-29 | Task 1 LOCALDATA 재확인 | 없음 — 행안부 1741000 목록·data.go.kr API/파일 검색·LOCALDATA(서비스 종료)·서울 열린데이터 모두 폐업일 있는 부동산중개업 원천 없음. brainstorming.md:196 정정 |
| 2026-09-29 | Task 2 실거래가 파일럿 | PASS — 아파트 매매 200/000/501건(강남구 2024-06) · 아파트 전월세 403 SERVICE_KEY_IS_NOT_REGISTERED_ERROR(미등록) · 상업업무용 매매 200/000/146건 |
| 2026-09-29 | Task 7 담배소매인 편의점 원천 게이트웨이 — Ruling P7 유령 행 드롭 | 폐업처리(2)·직권취소(3)·임시소매기간만료(4)·지정취소(5)인데 폐업일·취소일이 둘 다 없는 행 730건(전량) 적재에서 제외 — 그중 편의점 상호 55건이 영구 영업 유령 에피소드가 될 뻔했다. 정상영업(0)·휴업처리(1)·영업정지(6)는 임시 상태라 유지. 드롭 후 스모크: 동 427·기준일 2026-08-21·12개월전영업 7,842·개업 386·폐업 537·빈자리후보 255,343·막힘 168,657(66%)·영업중 7,691·에피소드 21,126 — 사전 조사(§2) 대비 전부 ±5% 이내 |
| 2026-09-29 | Task 10 아파트 매매 건수 수집 — `housing` BC·`apt_trade_count` | 마이그레이션 `e1f2a3b4c5d6` 적용 완료. 적재 전량 완료(백그라운드 `nohup`, 일일 한도 도달 없음) — `min(deal_ym)=202101` · `max(deal_ym)=202608`(68/68개월) · 16,367행 · `sum(trade_count)=283,839` |
