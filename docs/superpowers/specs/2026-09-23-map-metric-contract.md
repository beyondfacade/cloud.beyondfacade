# 지도 지표 계약 — 라우터가 늘어날 때 무엇을 베껴 쓸 것인가

> 작성 2026-09-23 · 대상 브랜치 `codex/seoul-atlas-landing` · 백엔드 v0.30.0~
> 선행: `2026-09-23-region-profile-design.md`(파생 지표), `2026-09-23-neighborhood-bc-design.md`
> 관련 구현: 백엔드 v0.27.0(`/profiles`), v0.29.0(`/commerce-changes`), 프론트 v0.15.0·v0.16.0

## 1. 왜 이 문서가 필요한가

v0.29.0에서 `/commerce-changes`를 열며 지도에 값을 공급하는 엔드포인트가 둘이 됐다. §12가
"라우터 하나, 테이블 하나"를 요구하므로 **앞으로도 원천이 늘면 엔드포인트가 는다.** 그 자체는
설계대로다. 문제는 새 엔드포인트가 각자 파라미터 이름과 응답 모양을 발명할 때다. 그러면
프론트엔드의 지표 레지스트리가 접착제가 아니라 늪이 된다.

이 문서는 **새 라우터가 발명하지 않고 베껴 쓸 계약 두 벌**과, 그 계약이 깨지는 지점(범주형),
레지스트리가 더는 못 버틸 때의 전환 조건을 정한다.

## 2. 라우터는 테이블 수가 아니라 화면 수요를 따른다

현재 테이블 13개에 라우터 3개다. "테이블마다 라우터"로 읽으면 10개를 더 만들어야 할 것 같지만
아니다.

| 테이블 | BC | 소비자 | 라우터 |
|---|---|---|---|
| `region_industry_metric` | metric | 지도·패널 | ✅ `/metrics` |
| `region_profile_quarter` | metric | 패널·지도(예정) | ✅ `/profiles` |
| `region_commerce_change` | neighborhood | 지도 | ✅ `/commerce-changes` |
| `region_industry_hour_gap_quarter` | metric | 패널 차트(예정) | 🔜 |
| `region_footfall/population/household/facility/spending_quarter` | neighborhood | **에이전트 게이트웨이 + 파생 배치** | ❌ 불필요 |
| `region_housing_average_quarter`·`seoul_commerce_change_baseline` | neighborhood | 에이전트 게이트웨이 | ❌ 불필요 |
| `region_commerce_sales/store/sales_breakdown` | commerce | 파생 배치 + 에이전트 | ❌ 불필요 |

**HTTP로 나갈 일이 없는 테이블에는 라우터를 만들지 않는다.** 에이전트는 `RegionFactsGateway`
(cross-BC 어댑터)로 프로세스 안에서 읽고, 파생 배치도 게이트웨이로 읽는다. 화면이 요구하기
전까지 인바운드를 열지 않는다. 실제로 열릴 것은 2~3개다.

### 2-1. 라우터의 고정비와 한계비용

v0.29.0은 숫자 하나를 위해 16파일을 깔았다. 그 16파일이 산 것은 **지표가 아니라 테이블**이다.
같은 테이블의 두 번째 지표(`closed_months`)를 더하는 비용은 백엔드 1줄 + 프론트 3줄이다.

```python
_METRIC_EXTRACTORS = {
    "operating_months": lambda row: row.operating_months,
    "closed_months": lambda row: row.closed_months,   # ← 두 번째부터는 이게 전부다
}
```

라우터를 낼지 말지는 "지표 하나 값어치가 있나"가 아니라 **"이 테이블을 화면에 열 것인가"**로
판단한다.

## 3. 계약 둘

새 엔드포인트는 아래 둘 중 하나를 베껴 쓴다. 이미 있는 셋(`/metrics`·`/commerce-changes`·
`/profiles/{region_code}`)이 이 모양이므로, 발명이 아니라 성문화다.

### 3-1. 단계구분도 계약 — 지도 색칠

```
GET /{resource}?metric=<name>&<축 파라미터>
200 → [{ "region_code": "1168064000", "value": 110.0 }]
404 → { "error": { "code": "METRIC_NOT_FOUND", "message": "지원하지 않는 metric: ..." } }
```

- **축 파라미터는 테이블마다 다르다.** `/metrics`는 `industry`+`year`, `/commerce-changes`는
  `year_quarter`다. 이걸 통일하려 들면 없는 축을 지어내거나 있는 축을 뭉개게 된다
- **시점을 생략하면 백엔드가 최신을 고른다.** 화면은 어느 분기·연도가 최신인지 모른다.
  프론트에 박으면 다음 적재 때 조용히 옛 시점을 보여준다
- **값이 없는 동은 행을 만들지 않는다.** 원천 공란을 0으로 내보내면 지도가 그 동을 척도의
  한쪽 끝으로 색칠한다 — "가장 빨리 닫는 동네"라는 거짓말이 된다
- 미지원 metric은 500이 아니라 404다. `metric` 디스패치는 if/elif가 아니라 extractor 테이블
  (GoF Strategy)로 한다

### 3-2. 상세 계약 — 사이드패널·리포트

```
GET /{resource}/{region_code}?<축 파라미터>
200 → 단일 객체 (또는 그 동에 속한 행 목록)
404 → { "error": { "code": "{RESOURCE}_NOT_FOUND", "message": "..." } }
```

- 시점 생략 시 최신 — 단계구분도 계약과 같은 이유
- 코드는 코드로 내보낸다. 화면에 띄울 이름·괄호 설명·툴팁은 프론트엔드가 갖는다
  (`industryLabel`·`neighborhoodTypeLabel` 전례). 예외는 **실제로 넘은 수치가 박힌 문장**
  (`type_reason`)뿐 — 그건 표현이 아니라 데이터다

### 3-3. 새 라우터를 열 때의 순서

§12대로 `myself`부터 만든다. 하드코딩 데이터를 router → use_case → interactor → port →
repository로 왕복시켜 배선을 먼저 확인하고, 그다음 실제 계약을 붙인다.

## 4. 다음에 열릴 것 셋

| 순서 | 엔드포인트 | 테이블 | 계약 | 비용 |
|---|---|---|---|---|
| 1 | `GET /profiles?metric=&year_quarter=` | `region_profile_quarter` | 3-1 | 기존 라우터에 목록 경로 1개. **새 라우터 없음** |
| 2 | `GET /profiles/types?year_quarter=` | 같은 테이블 | 3-1의 범주형 변종(§5) | 경로 1개 |
| 3 | `GET /hour-gaps?region=&industry=&year_quarter=` | `region_industry_hour_gap_quarter` | 3-2 | 새 라우터 1벌 |

**1번이 이 문서에서 가장 값이 크다.** `region_profile_quarter`에 숫자 컬럼 7개가 이미 들어
있다 — `worker_resident_ratio` · `weekend_index` · `night_index` · `footfall_20s_share` ·
`fnb_share` · `facility_total` · `resident_total`. 새 테이블도 새 라우터도 없이 **extractor
7줄로 지도 지표 7개가 열린다.** 파생 계층(v0.26.0)을 만든 값이 여기서 돌아온다.

3번은 단계구분도가 아니다. 동×업종의 시간 구간 6행이라 지도가 아니라 패널 차트다. 3-1에
우겨넣지 않는다 — 계약이 맞지 않으면 계약을 늘리는 게 아니라 다른 계약을 쓴다.

## 5. 범주형 — 경로를 나눈다

동네 유형 6종을 지도에 올리면 `value: number`가 맞지 않는다. 색도 분위수 스케일이 아니라 범주
팔레트여야 하고, 범례도 값 구간이 아니라 이름 6줄이다.

**한 응답에 섞지 않는다.**

```
GET /profiles?metric=night_index   → [{ region_code, value }]        숫자 계약 그대로
GET /profiles/types?year_quarter=  → [{ region_code, type_code }]    범주 계약
```

같은 테이블이므로 §12는 지켜진다(라우터 하나, 테이블 하나). `{ region_code, value, category }`
한 객체에 담고 한쪽을 null로 두는 안은 버린다 — 타입이 거짓말하는 구조이고, 소비하는 쪽이
매번 어느 쪽이 채워졌는지 확인해야 한다.

프론트엔드는 `METRIC_SOURCES` 항목에 `kind: "numeric" | "categorical"`을 더하고 지도 표현식과
범례가 그 필드로 분기한다. `if`가 아니라 테이블 조회다.

## 6. 프론트엔드 레지스트리 — 지금과 전환 조건

`features/map-explorer/lib/metric-sources.ts`가 "어느 지표가 어디서 오는지"를 아는 **유일한
자리**다. 이 seam을 늘리지 않는다 — 컴포넌트가 직접 `fetchMetrics`를 부르기 시작하면 끝이다.

지표 하나당 프론트가 아는 것은 다섯이다: 목록(`METRICS`) · 라벨(`METRIC_LABELS`) ·
색 스킴(`SCHEME_BY_METRIC`) · 표기 형식(`FORMAT_BY_METRIC`) · 원천(`METRIC_SOURCES`).

**드리프트가 한 방향으로만 막혀 있다.** `metric-sources.test.ts`는 "프론트가 고른 지표에 원천이
있나"를 잡지만, **백엔드가 지원하는데 프론트가 안 보여주는 경우는 못 잡는다.**

### 전환 조건 — 이 중 하나가 실제로 일어나면 카탈로그로 간다

1. 백엔드에 추가한 지표가 화면에 안 나타나는 일이 실제로 발생
2. 지도 지표가 8개를 넘음

그때 `master` BC에 `map_metric` 시드 테이블을 만들고 `GET /map-metrics`로 카탈로그를 내린다 —
`metric_id` · `label_ko` · `unit` · `kind` · `axis` · `source_path` · `color_scheme` ·
`note_ko`. 지표 추가가 **시드 1행 + extractor 1줄**이 되고 프론트는 건드리지 않는다. 이것도
§12를 지킨다(라우터 하나, 테이블 하나).

**지금 만들지 않는다.** 지표 4개에 카탈로그는 §2 위반이다. 조건을 적어두는 것이 지금 할 일이다.

## 7. 범위 밖

- `map_metric` 카탈로그 구현 — §6의 전환 조건이 충족될 때
- 화면에 어느 지표를 노출할지 — 백엔드가 7개를 지원한다고 컨트롤바에 버튼 7개를 더하는 것은
  아니다. UI 노출은 별도 판단
- 지출 항목 구성비 — 본사·온라인 가맹점 필터가 선행 (`2026-09-23-spending-definition.md`)

## 8. 완료 기준

- §3의 계약 두 벌이 문서로 존재하고, 이후 새 엔드포인트가 이를 따른다
- §4의 1번(`GET /profiles?metric=`)이 구현되고 extractor 테이블로 7개 지표를 연다
- 값 없는 동 제외·시점 생략 시 최신·미지원 metric 404가 테스트로 고정된다
- 프론트엔드가 `METRIC_SOURCES` 밖에서 지표 원천을 알지 못한다
