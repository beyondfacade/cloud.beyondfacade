# 무대 — 관문이 내려놓는 지도와 패널

> 작성 2026-09-23 · 브랜치 `feat/map-stage` · 백엔드 v0.32.0~ / 프론트 v0.19.0~
> 선행: `plans/2026-09-23-chat-first-roadmap.md`(T2) · `specs/2026-09-23-map-metric-contract.md`(계약 두 벌, 범주형 §5)
> · `specs/2026-09-23-chat-first-direction.md`(관문이 `/map?region&industry&budget`로 착지)
> · `specs/2026-09-23-region-profile-design.md`(유형 6종·시간대 라벨) · `specs/2026-09-23-neighborhood-typology.md` §6(4블록·정점→바닥 서사)

## 1. 목적 — 데이터의 축이 바뀌었는데 화면은 옛 축이다

이번 데이터(v0.23~v0.30)의 주어는 **동네**고 시간은 **분기 + 하루 안의 시간대**다. 화면은 여전히
업종 셀렉터 + 연도 셀렉터 + 업종 지표 3개로 짜여 있다. 영업 지속 개월을 얹으며 "업종 무관" 단서를
달아야 했던 게 첫 균열이고, 파생 지표 7종이 열리면서 지표 과반이 업종·연도 셀렉터와 무관해졌다.
각주로 덮을 크기가 아니다.

관문(T1)이 사용자를 **동이 선택된 상태로** 내려놓는다. 그러면 패널이 첫 화면이다. 창업자의 질문
순서대로 무대를 다시 세운다.

| # | 질문 | 데이터 | 지금 화면 |
|---|---|---|---|
| 1 | 어디를 볼까 | 동네 유형 6종 | ❌ 지도는 폐업률 |
| 2 | 여기 어떤 동네야 | 유형 + 근거 | ✅ 패널 |
| 3 | 하루가 어떻게 흘러 | 4블록 강도 + 정점→바닥 | △ 문장 한 줄 |
| 4 | 내 업종은 언제 돈이 돌아 | 시간대 어긋남 34만 행 | ❌ **없음** |
| 5 | 여기 오래 버텨 | 영업/폐업 개월 + 상권변화 | △ 지도만 |
| 6 | 그래서 어쩌라고 | AI 리포트 | ✅ |

## 2. 하지 않을 것

- 파생 지표 7종 전부 버튼화 — 지도는 "어디"를 고르는 도구, 근거 수치는 패널 몫
- 매출 지표를 지도에 — 점포수와 무상관이라 폐기됨(교차검증 문서)
- 시간대 어긋남을 지도에 — 동×업종×6구간이라 단계구분도가 아니다
- 차트 라이브러리 도입 — 의존성이 `maplibre-gl`·`react-query`·`react-markdown`뿐이다. 막대 4개와
  선 2개는 손으로 그린 SVG 60줄이면 된다

## 3. T2-1 유형 단계구분도 — 범주형 계약의 첫 구현

### 3-1. 백엔드 `GET /profiles/types?year_quarter=`

`map-metric-contract` §5대로 **경로를 나눈다.** `/profiles?metric=`(숫자)과 별개다.

```
200 → [{ "region_code": "1168064000", "type_code": "office" }]   분기 생략 시 최신
```

같은 `region_profile_quarter`이므로 §12는 지켜진다(라우터 하나, 테이블 하나). 유스케이스
`RegionProfileUseCase.list_types(year_quarter)` + 레포지토리 `list_by_quarter` 재사용. `type_code`는
코드다 — 이름·색은 프론트가 갖는다.

### 3-2. 프론트 — 범주 팔레트와 범주 범례

- `shared/api/types.ts`에 `CategoryRow {region_code, type_code}`. `MapMetricKey`에 `"neighborhood_type"`
  추가. `METRIC_SOURCES` 항목에 `kind: "numeric" | "categorical"`을 더하고 `fetch`의 반환을
  `MetricRow[] | CategoryRow[]`로 둘로 나눈다 — 한 타입에 `value`/`category`를 섞어 null로 두지 않는다.
- `lib/metric-color.ts`에 `makeCategoryColorScale(codes)`를 **별도 함수**로 둔다. 분위수 스케일과
  코드를 섞지 않는다. `colorOf(code)`와 `classes[{color, label}]`가 같은 객체를 공유하는 원칙은 같다.
- **팔레트 6색**은 `lib/neighborhood-palette.ts`에 라이트/다크 둘 다 둔다(UI 토큰과 분리된 데이터
  시각화 체계 — `tokens.css` 상단 주석이 이미 이렇게 선언한다). `data-theme` 감지는 기존
  `MutationObserver` 패턴(§16·§18). 원칙: **주거형이 60%라 지도를 지배한다 → 주거형을 가장 옅게**,
  나머지 5종이 튀게. 색맹 구분을 위해 명도 차를 두고, 범례가 필수다(6색은 색만으로 못 가른다).
- `map-view.tsx`의 `match` 표현식은 그대로 쓴다 — `colorOf`가 코드를 받을 뿐이다.
- `map-legend.tsx` — `kind`가 `categorical`이면 값 구간 대신 **이름 6줄**(`neighborhoodTypeLabel`의
  `name` + 괄호 설명). "데이터 없음" 행은 유지(`region_code` NULL 옛 행정동 3개).
- `DEFAULT_STATE.metric`을 `"neighborhood_type"`으로 바꾼다 — 창업자가 처음 묻는 건 "어디가 망하나"가
  아니라 "어디가 어떤 곳이냐"다. E2E 스크립트의 기본 지표 전제가 있으면 같이 고친다.
- mock `/api/mock/profiles/types` — `regionProfileOf`의 `neighborhood_type`을 그대로 씀.

## 4. T2-2 컨트롤바 두 무리 — 셀렉터가 지표의 축을 정직하게 따라간다

```
동네   [유형] [심야 체류] [음식·유흥 비중] [영업 지속]     ← 분기 축 · 업종 셀렉터 비활성
업종   [폐업률] [성장률] [점포수]                          ← 연 축 · 업종 셀렉터 활성
```

- 명시적 모드 토글이 아니다. **버튼 무리 자체가 모드다.** `METRICS`를 `METRIC_GROUPS =
  [{label:"동네", axis:"region_quarter", metrics:[…]}, {label:"업종", axis:"industry_year", metrics:[…]}]`로
  바꾸고 컨트롤바는 그룹을 순회한다. `METRIC_SOURCES`의 `axis`와 같은 값을 쓴다.
- 동네 무리가 선택되면 업종 `select`는 **`disabled`가 아니라 흐리게** 둔다 — 사이드패널·마커가 계속
  업종을 쓰므로 값은 살아 있어야 한다. `aria-describedby`로 "이 지표는 업종과 무관합니다"를 붙인다.
  v0.17.0의 범례 단서("업종 구분 없는 동 전체 평균")는 무리 구조가 그 뜻을 말하므로 **뺀다.**
- 시간 셀렉터: 동네 무리는 분기(`20211`~최신, "2026년 2분기" 표기), 업종 무리는 연도. `MapState`에
  `year_quarter: string | null`을 더한다. 갈림길 ①의 결정 — 연 데이터를 분기로 위장하지 않는다.
- 동네 지표 4종의 `METRIC_SOURCES`: 유형 → `/profiles/types`, 심야 체류·음식유흥 → `/profiles?metric=`,
  영업 지속 → `/commerce-changes`. 나머지 파생 5종은 API에만 있고 버튼이 없다(§2).

## 5. T2-3 패널 서사 재배열 + "얼마나 버티나"

지금 `업종 카드 3 → 동네 프로필 → 업종 섹션 → 버튼`. 질문 순서로:

```
① 어떤 동네인가        유형 · 괄호 · 근거 문장                       (있음, 맨 위로)
② 하루가 어떻게 흐르나  4블록 막대 4개 + 정점→바닥 서사                (막대 신규 — §5-1)
③ 내 업종은 언제 도나   6구간 유동 vs 매출 두 선                       (T2-4)
④ 얼마나 버티나        영업 110 / 폐업 48개월 · 상권변화 배지           (신규 — §5-2)
⑤ 업종 실적           점포수 · 폐업률 · 성장률 (+ 스냅샷 안내)          (있음, 아래로)
⑥ AI 분석 →
```

### 5-1. 4블록 막대

`GET /profiles/{region_code}`에는 블록 강도가 없다(라벨·정점·바닥만). 두 길 중 **응답에 4블록 강도를
더한다** — `RegionProfileResponse`에 `block_intensities: {morning, day, evening, night} | null`(추가만,
하위 호환). 배치가 이미 계산하는 값이라 `region_profile_quarter`에 컬럼 4개를 더하고 마이그레이션
1개(`c5d6e7f8a9b0` 자식). 프론트가 원값에서 다시 계산하지 않는다 — 시간당 보정을 두 곳에서 하면
언젠가 한 곳이 틀린다.

막대는 SVG `<rect>` 4개, 1.0 기준선 하나. 정점 블록만 강조색.

### 5-2. 얼마나 버티나 — `GET /commerce-changes/{region_code}` (상세 계약)

`map-metric-contract` §3-2. `{region_code, year_quarter, change_code, change_name, operating_months,
closed_months}` + 같은 분기의 서울 평균(`seoul_commerce_change_baseline`)을 `seoul: {operating_months,
closed_months}`로 동봉한다 — "110개월"은 "서울 117개월"이 옆에 있어야 읽힌다. 분기 생략 시 최신,
404 `COMMERCE_CHANGE_NOT_FOUND`. neighborhood BC query 포트에 `find_latest(region_code)`와 baseline
조회를 더한다(baseline은 별도 테이블이므로 별도 포트 — ISP).

패널: "영업 110개월 · 서울 117" / "폐업까지 48개월 · 서울 52" 두 줄 + 상권변화 배지 4종(다이나믹·정체·
상권확장·상권축소 — 이름은 `change_name` 그대로, 색은 UI 토큰 `--ok/--warn/--danger/--text-secondary`).

## 6. T2-4 시간대 어긋남 — 이 프로젝트의 단독 능력

### 6-1. 백엔드 `GET /hour-gaps?region=&industry=&year_quarter=` (상세 계약)

metric BC에 `region_industry_hour_gap` 프랙탈의 나머지 3파일(schema·inbound mapper·router).
`myself` 먼저(§12). 유스케이스 `list_latest_bands`(T1-1이 추가)와 `list_bands`를 그대로 쓴다.

```
200 → { "region_code", "industry_id", "year_quarter",
        "bands": [ { "hour_band": "06_11", "footfall_intensity": 1.003, "sales_intensity": 0.704, "gap": -0.299 }, … 6 ] }
404 → { "error": { "code": "HOUR_GAP_NOT_FOUND" } }   그 동에 그 업종 매출이 없음
```

분기 생략 시 그 조합의 최신(20254까지). 응답에 `year_quarter`를 반드시 적는다 — 프로필(20262)과 다르다.

### 6-2. 프론트 — 두 선을 그린다, gap 하나를 그리지 않는다

v0.26.0 검증에서 **어긋남의 신호는 절대 부호가 아니라 상대 위치**임이 확인됐다(업무형 카페 06_11
gap은 음수지만 6유형 중 1위). gap 막대 하나로 그리면 "카페는 아침에 음수"라는 오독을 낳는다.
**유동 강도와 매출 강도 두 선**을 6구간 위에 겹쳐 그려 어긋남이 눈에 읽히게 한다. 1.0 기준선.
구간 라벨은 intent BC 어휘("점심(11~14시)")와 같은 한국어 — 프론트 `shared/neighborhood.ts`에
`HOUR_BAND_LABELS`를 더한다.

문장 한 줄을 곁들인다 — 결정론: "사람은 {유동 최대 구간}에 가장 많고, 돈은 {매출 최대 구간}에
돕니다." 두 구간이 같으면 "사람과 돈이 {구간}에 같이 몰립니다." 관문의 `diagnosis`와 같은 어휘.

섹션은 업종에 따라 바뀌므로 `industry` prop을 받는다. 404면 "이 동네엔 {업종} 매출 자료가 없습니다"
한 줄(스냅샷 업종 안내와 같은 톤). mock `/api/mock/hour-gaps` — 유형별 고정 프로파일(업무형은
낮 정점, 주거형은 저녁)로 결정적 생성.

## 7. T2-5 리포트 `market`에 비교 기준 주입

패널 ①~④와 리포트 market 슬롯의 재료가 같다. 사용자가 패널에서 본 걸 리포트에서 또 읽으면 진전이
없다고 느낀다. 리포트는 **패널이 안 보여주는 것**을 말해야 한다 — 서울 평균 대비, 유형별 중앙값 대비.

`RegionFactsGateway.neighborhood_profile()` 결과에 `benchmarks`를 더한다:
- `seoul: {operating_months, closed_months}` (baseline 테이블)
- `type_median: {weekend_index, night_index, fnb_share, worker_resident_ratio}` — 같은 분기·같은 유형
  422동 중앙값. 배치 때 계산해 두는 게 맞지만 지금은 게이트웨이가 한 번 집계한다(422행, 싸다).
  느려지면 `region_type_benchmark_quarter`로 승격.

`SYSTEM_PROMPT` market 계약에 한 줄 — "동네 설명과 주의점은 `benchmarks`와 비교해 쓴다. 비교 없는
절대값 서술은 하지 않는다." `caveats` 원칙과 같다: 해당하는 비교만.

## 8. 순서와 의존

```
T2-1 유형 단계구분도 ─┐
                      ├─ T2-2 컨트롤바 두 무리 (둘 다 map-state·control-bar·legend를 만진다 — 한 브랜치, 순서대로)
T2-4 hour-gaps 라우터 ─┘─ T2-3 패널 서사 (③이 T2-4를 넣는다)
T2-5 리포트 벤치마크 — 독립, 백엔드만
```

T2-4 백엔드는 T1-3이 이미 유스케이스를 만들어둬 라우터 3파일이 전부다 — **먼저 한다.** 그다음
T2-1 → T2-2 → T2-3 → T2-5. 커밋은 다섯.

## 9. 검증

1. `/profiles/types` 422행, 유형 6종 합이 422, `/profiles?metric=`과 같은 분기
2. 팔레트 — 라이트/다크 각각 6색이 서로 구분되는가(명도 차 스냅샷), 주거형이 가장 옅은가
3. 기본 지표가 유형이고 URL 없이 열어도 유형 범례가 뜨는가
4. 동네 무리 선택 시 업종 `select`가 살아 있되 흐린가, 시간 셀렉터가 분기로 바뀌는가, 업종 무리로
   돌아오면 연도로 돌아오는가. `budget`이 전 과정에서 URL에 남는가(T1-2 테스트 재사용)
5. `/hour-gaps` — 역삼1동×카페 6행, 없는 조합 404, 분기 생략 시 20254
6. 두 선 SVG — 6점씩 두 경로, 1.0 기준선, 문장이 유동/매출 최대 구간을 맞게 고르는가
7. `/commerce-changes/{region}` — 서울 평균 동봉, 404
8. 리포트 — `benchmarks`가 도구 결과에 있고 프롬프트 계약에 비교 지시가 있는가(기존 슬롯 테스트 확장)
9. 실 백엔드로 관문 → 착지 → 패널 ①~⑤가 한 화면에 뜨는 E2E 1단계 추가

## 10. 범위 밖

- 파생 지표 나머지 5종 버튼 · 매출 지표 지도 · 어긋남 지도(§2)
- `region_type_benchmark_quarter` 테이블 (느려지면)
- 카탈로그 (`map-metric-contract` §6 전환 조건)
- 모바일 레이아웃 (패널이 길어진다 — 별도)

## 11. 완료 기준

- 관문에서 A유형으로 착지하면 지도는 유형으로 색칠돼 있고 패널 ①~⑤가 순서대로 뜬다
- 동네/업종 무리 전환이 셀렉터의 축을 바꾼다. "업종 무관" 단서 문구가 사라져도 오해가 없다
- 시간대 어긋남이 두 선으로 보이고 문장이 두 최대 구간을 말한다
- 리포트 market 절이 서울 평균·유형 중앙값 대비로 쓰인다
- ver_log 백엔드 v0.32.0(hour-gaps·types·commerce-change 상세·benchmarks) · 프론트 v0.19.0
