# 계획 — "그래서 얼마가 필요한가"를 실측에서 출발시킨다

> 작성 2026-09-23 · 브랜치 `feat/finance` · 백엔드 v0.33.0~ / 프론트 v0.22.0~
> 선행: `plans/2026-09-23-chat-first-roadmap.md`(T3) · `specs/2026-09-23-chat-first-direction.md`(관문이 `budget`을 URL에 싣는다)
> · `specs/2026-09-23-map-stage-design.md`(무대) · `specs/2026-09-23-commerce-bc-design.md`(매출·점포·업종 매핑)
> 참조 구현: `~/projects/cloud.localhostdaegu` `backend/apps/finance/domain/engine.py`(결정론 엔진, 자작),
> `frontend/src/features/simulator/`(폼·비교·상담 초안), `docs/problem.md`(함정 셋)

## 1. 목적 — 상권 분석의 다음 층

무대(①②)가 "여기가 어떤 곳이고 언제 돈이 도나"를 답한다. 창업자의 다음 질문은 **"그래서 얼마가
필요한가"**다. 대구 분화본이 이 층을 만들었고 그 판단 셋을 그대로 가져온다.

- **계산은 코드가, 설명만 AI가.** 결정론 엔진이 표를 만들고 LLM은 읽고 설명한다. 숫자 환각이 구조적으로
  불가능하다.
- **금융연계는 "상품 매칭"이 아니라 "조정한 계획"이다.** 위험 진단에서 대출 상품으로 직행하면 비용
  축소·계획 보류라는 판단이 빠진다. 최초안을 고정하고 조건을 바꿔 비교한 뒤 상담할 안을 고른다.
- **부족액 0원 함정.** 희망대출을 넣으면 "충분합니다"가 뜨는데 그 돈은 아직 빌리지 않은 돈이다.
  헤드라인은 `funding_gap`이 아니라 **`external_funding_need`(자기자본 외 조달 필요)**다.

그리고 대구가 못 한 것을 한다. 대구 엔진 입력 13개 중 사용자가 가장 못 채우는 게
`expected_monthly_revenue`인데, 대구는 매출 데이터가 없어 물어볼 수밖에 없었다. 우리는
`region_commerce_sales ÷ region_commerce_store ÷ 3`으로 **그 동·그 업종 점포당 평균 월매출**을 준다.
손익분기·조달 필요액이 사용자의 상상이 아니라 실측에서 출발한다.

## 2. 어디에 둘 것인가 — 테이블 없는 BC, 두 번째

`apps/finance`. **ERD 테이블이 없다.** intent BC와 같은 §12 예외이며 근거도 같다 — 계산은 상태가 없다.
프리필은 commerce·rent·shock(금리)·master를 읽을 뿐 쓰지 않는다. 계획 초안은 브라우저
`sessionStorage`에 산다(대구 §5-3과 같음; 로그인이 없는데 서버 테이블은 이르다). 로그인이 생기면
`finance_plan` 테이블과 함께 11파일 세트로 승격한다.

읽기 방향 `finance` → `commerce`·`rent`·`shock`·`master` 단방향, 게이트웨이 안에서만.

## 3. 엔진 — 대구 `engine.py` 이식

80줄, 테스트 있음, 자작. `domain/services/engine.py`로 **그대로** 옮기고 docstring에 출처를 적는다.
산식을 바꾸지 않는다 — 두 프로젝트가 같은 수를 내야 서로 검산이 된다.

```
CAPEX            = 보증금 + 권리금 + 인테리어 + 설비
월 고정비          = 월세 + 대출이자(희망대출 × 금리 ÷ 12) + 보험 + 인건비
변동비율           = 원가율 + 수수료율
BEP 매출          = 고정비 ÷ (1 − 변동비율)
운영준비금         = 고정비 × 6개월
총 준비자금        = CAPEX + 운영준비금
자기자본 외 조달 필요 = max(0, 총 준비자금 − 자기자본)               ← 헤드라인
희망대출 반영 후 부족액 = max(0, 총 준비자금 − 자기자본 − 희망대출)   ← 보조
시나리오 비관·기준·낙관 = 기준 매출 × 0.6 / 1.0 / 1.6 → 영업이익·회수기간·런웨이
금리 스트레스 +1%p / +2%p
```

## 4. 계약

### 4-1. `GET /finance/myself` — §12 배선 검증

### 4-2. `POST /finance/simulate`

요청 = 대구 `FinanceInput` 13필드 그대로(`deposit`·`key_money`·`interior_cost`·`equipment_cost`·
`monthly_rent`·`monthly_payroll`·`monthly_insurance`·`cost_ratio`·`fee_ratio`·`equity`·`desired_loan`·
`loan_rate`·`expected_monthly_revenue`). 응답 = 대구 `FinanceResult` 그대로(`capex`·`monthly_fixed`·
`bep_revenue`·`funding_gap`·`reserve_months`·`operating_reserve`·`total_required_funds`·
`external_funding_need`·`scenarios[3]`·`stress[2]`). 서버가 계산한다 — 클라이언트 계산 결과를 신뢰하지
않는다(대구 §②).

### 4-3. `GET /finance/prefill?region=&industry=` — 이 문서의 새 것

값마다 **출처(`basis`)와 단서(`caveat`)**를 붙인다(`docs/후보.md` 항목 1 "값마다 출처 배지").
화면은 값을 채우되 "어디서 온 값인지"를 항상 보인다.

```json
{
  "region_code": "1168064000", "industry_id": "cafe",
  "expected_monthly_revenue": {
    "value": 29439538,
    "basis": { "year_quarter": "20254", "quarterly_sales": 35327445013, "store_count": 400,
               "source_codes": ["CS100010", "CS100006", "CS100008"] },
    "caveat": "이 동 카페 400곳의 분기 매출을 점포 수로 나눈 평균입니다. 편차가 크고 신규 점포는 평균 아래서 시작하는 경우가 많습니다."
  },
  "rent_per_m2": {
    "value": 52.46, "unit": "천원/㎡/월",
    "basis": { "region_path": "서울>강남", "building_type": "medium_large", "period": "2026Q2", "level": "권역" },
    "caveat": "행정동 단위 임대료 자료가 없어 강남 권역(R-ONE) 평균입니다. 실제 매물과 다를 수 있습니다."
  },
  "cost_ratio":  { "value": 0.35, "basis": { "kind": "industry_benchmark" }, "caveat": "업종 평균 근사값입니다. 원가 구조를 알면 고치세요." },
  "loan_rate":   { "value": 0.048, "basis": { "rate_type": "loan_facility", "period": "202607", "source": "ECOS" }, "caveat": "공시 평균 금리입니다. 실제 심사 금리와 다릅니다." },
  "equity": null
}
```

- **월매출** — `industry_source_code`(seoul_commercial)에 매핑된 CS 코드 **전부**의 `sales_amount` 합 ÷
  `store_count` 합 ÷ 3. 카페는 3코드(v0.26.0에서 보정한 매핑)다. 두 테이블이 모두 있는 최신 분기.
  없으면 `null`(사용자가 입력).
  ⚠ **확인 절차**: `sales_amount`가 분기 합인지 월 값인지 원천 컬럼명이 "당월_매출_금액"이라 혼동
  여지가 있다. `commerce-bc-design.md`의 결정과 실측 타당성(역삼1동 커피 2,944만/월 — 월 값이었다면
  8,800만/월로 비현실적)으로 **분기 합**임을 구현 전에 못 박고 주석에 근거를 남긴다.
- **임대료** — R-ONE은 상권(83)·권역(4)·시도(1) 단위이고 동 매핑이 없다. **구 → 권역 매핑표**
  (`domain/value_objects/rent_zones.py`, 25구): 강남=강남·서초·송파(·강동?), 도심=종로·중구·용산,
  영등포신촌=영등포·마포·서대문, 나머지=기타. 매핑표는 R-ONE 권역 정의 문서로 검증하고 출처를 적는다.
  권역의 최신 `rent_per_m2`(중대형 기본, 소규모도 응답에 같이). 사용자는 **면적(㎡)**을 넣고 화면이
  `월세 = rent_per_m2 × 면적 × 1,000`을 계산해 프리필한다(기본 33㎡, 수정 가능).
- **원가율** — `domain/value_objects/cost_ratios.py`, 우리 10업종. 대구 값을 겹치는 업종에 쓰고
  (cafe 0.35·hair_salon 0.25·gym 0.15·billiard 0.20·karaoke 0.20·pc_bang 0.20) 나머지 4종(academy·
  childcare·convenience_store·real_estate)은 근사값과 근거를 주석에 적는다. 전부 "근사"다.
- **금리** — `interest_rate`의 `loan_facility` 최신(시설자금 = 상가 관련 최근접). `shock` BC를 게이트웨이로.
- **자기자본** — 관문의 `budget`이 URL로 온다. 프리필 응답은 `null`, 화면이 URL에서 채운다.

## 5. 프론트엔드 `/plan`

`features/plan/`. 대구 `simulator/`의 구조를 가져오되 **상담 프로필·상품 매칭은 T4로** 미룬다.

```
① 프리필 확인    13필드 폼. 프리필된 값엔 출처 배지("실측 · 20254 · 400점포" / "R-ONE 강남 권역" / "ECOS 202607").
                 비어 있는 필수값(보증금·인테리어·희망대출)만 사용자가 채운다. 면적 → 월세 자동 계산
② 계산           POST /finance/simulate → 네 갈래(총 준비자금 · 조달 필요 · 부족액 · BEP) + 시나리오 3 + 스트레스 2
                 헤드라인은 "자기자본 외 조달 필요". "충분합니다" 문구는 쓰지 않는다
③ 최초안 고정     첫 성공 계산 = 최초안. 이후 수정·재계산 = 현재안. 수정 후 미계산 상태에선 비교·선택 잠금
④ 비교           최초안 vs 현재안 표 + 사용자가 쓴 변경 이유(추정하지 않는다)
⑤ 다음           "조달·상담 준비 →" (T4). 그전엔 요약 Markdown 복사만
```

- `lib/consultation-draft.ts` 이식(`sessionStorage`, 최초안/현재안/선택/변경 이유, `unconfirmed` 필드 기록).
  키 `beyondfacade.plan.v1`.
- 진입: 사이드패널 CTA 둘 — "AI 분석 →"(기존) 옆에 **"자금 계획 →"**(`/plan?region&industry&budget`).
  관문 `diagnosis-line`에도 같은 링크. 랜딩 3단계 카피(동네 → 계획 → 상담)는 T4에서 같이 손본다.
- `budget`은 `MapState`에 실려 있으니(T1-2) 지도에서 지표를 바꿔도 살아 있다.
- mock `/api/mock/finance/{simulate,prefill}` — simulate는 엔진을 TS로 한 벌 더 두지 않는다. **mock도
  같은 산식을 써야 하므로** `lib/finance-engine.ts`(엔진 TS 이식, 테스트로 파이썬과 같은 수 확인)를
  mock 라우트가 import한다. 화면은 이 TS 엔진을 쓰지 않는다 — 서버 결과만 믿는다.

## 6. T3-3 — 리포트 `calculator` 절이 엔진을 읽는다

agent BC의 `compare_rent_vs_buy`(월세 대 매입 한 축)를 **finance 엔진 도구로 흡수**한다.
`run_finance_simulation` 도구가 13필드를 받아 finance BC 유스케이스를 호출(게이트웨이 경유), 결과 표를
LLM에 준다. `calculator` 절의 프롬프트 계약: "표의 수치를 그대로 인용하고 다시 계산하지 않는다".
`compare_rent_vs_buy`는 제거하지 않고 남긴다 — 다른 질문(매입)에 여전히 답한다.

## 7. 검증

1. 엔진 — 대구 테스트 이식 + 대구 시연 대본의 사례(월세 250 → BEP 900만·조달 필요 3,160만·부족 660만;
   월세 100 → BEP 525만·부족 0)를 **그대로** 재현
2. 프리필 — 역삼1동×카페 월매출 3코드 합산값, 매출 없는 조합 null, 권역 매핑 25구 전부 4권역 중 하나,
   금리 최신 period
3. 계약 — myself·simulate·prefill 404/422
4. 프론트 — 프리필 배지 렌더, 최초안 고정·수정 후 잠금·비교표, `sessionStorage` 왕복, mock 엔진 =
   파이썬 엔진 같은 수(사례 2건)
5. 실 백엔드 — 관문 "역삼동에 카페, 예산 5천" → 착지 → `/plan` → 자기자본 5,000만·월매출 2,944만 프리필
   → 계산 → 조달 필요 헤드라인. E2E에 `[9]` 단계로 추가

## 8. 범위 밖

- 상담 프로필(사업자등록·개업일), 상품 후보, 확인할 질문, 준비자료 저장 — **T4**
- `finance_plan` 테이블·로그인
- 임대료의 동 단위 해상도(국토부 상업용 실거래가 — HANDOFF 포스트MVP)
- 인건비 벤치마크(자료 없음 — 사용자 입력)

## 9. 완료 기준

- 대구 시연 사례를 우리 엔진이 같은 수로 재현한다
- 관문에서 `/plan`까지 예산·월매출·임대료·금리가 출처 배지와 함께 프리필돼 있다
- 헤드라인이 "자기자본 외 조달 필요"이고 "충분합니다"가 어디에도 없다
- 최초안/현재안 비교와 변경 이유가 `sessionStorage`에서 살아남는다
- ver_log 백엔드 v0.33.0 · 프론트 v0.22.0
