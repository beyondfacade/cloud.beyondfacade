# 채팅 관문 — 한 문장에서 출발하는 상권 분석

> 작성 2026-09-23 · 브랜치 `feat/intent-gate` · 백엔드 v0.31.0~ / 프론트 v0.18.0~
> 선행: `plans/2026-09-23-chat-first-roadmap.md`(T1), `specs/2026-09-23-map-metric-contract.md`(계약 두 벌)
> 참조 구현: `~/projects/cloud.localhostdaegu` `apps/intent`·`features/intent-gate` (2026-09-18, 대구 해커톤 분화본)

## 1. 목적

지금 진입은 지도다. 사용자가 업종·지표·연도를 고르고 동을 클릭해야 첫 정보가 나온다. 대구 분화본이
증명한 대로 **입력창 하나가 그 마찰을 없앤다** — "역삼동에 카페, 예산 5천"이면 동·업종·예산이
한 번에 잡히고 지도는 확인하러 가는 곳이 된다.

우리는 한 발 더 간다. 파싱 결과만으로 `region_profile_quarter`와 `region_industry_hour_gap_quarter`를
읽어 **지도를 보기 전에 한 줄을 먼저 말한다.**

> "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다."

대구는 매출도 유형도 없어서 못 한 단계다. 이것이 관문의 존재 이유이고, 그래서 관문은 `intent` BC가
아니라 이 문장까지 포함해서 설계한다.

## 2. 대구에서 가져오는 것과 바꾸는 것

| | 대구 | 우리 |
|---|---|---|
| 구조 | 입력창 → `POST /intent` → 되묻기 칩 → `/map?…` 착지 | **같다** |
| 파서 | 순수 규칙(랜드마크 16 + 동·구 + 업종 동의어 + 예산 정규식) | 규칙 먼저, **랜드마크·자유문만 LLM 1콜** |
| 지역 키 | (동 이름, 구 코드) 쌍 — 동명이동이 많다 | **동 이름 하나** — 427개 중 중복은 `신사동`(강남·관악) 하나 |
| 라우팅 단위 | 구(`district`) | **동(`region`)** — 구는 되묻기 칩에만 쓴다 |
| 응답 | 의도·코드·결측 | + **`diagnosis` 한 줄** + `source`(rule/llm) |
| 상태 | URL | URL — `budget`을 `MapState`에 실어 잃지 않는다 |

가져오지 않는 것: 위험도 점수, `district` 파라미터, 대구 랜드마크 사전.

## 3. 어디에 둘 것인가 — 테이블 없는 BC

`apps/intent`를 새로 둔다. **ERD 테이블이 없다.** §12 "1 테이블 = 1 프랙탈"의 의도적 예외이며
근거는 이렇다 — 파싱은 상태가 없다. 마스터(`region`·`district`·`industry`)를 읽고 파생(`profile`·
`hour_gap`)을 읽을 뿐 아무것도 쓰지 않는다. 대구도 같은 판단이었다.

파싱 로그(`intent_log`)로 "사람들이 뭘 묻는가"를 남기는 건 값이 있지만 **지금은 만들지 않는다.**
필요해지면 그때 테이블과 함께 11파일 세트로 승격한다.

프랙탈 중 쓰는 것: `domain/`(파서·추출기·문장 조립) · `app/dtos` · `app/ports/input`(UseCase) ·
`app/ports/output`(마스터 조회·파생 조회·LLM 추출 3포트) · `app/use_cases` · `adapter/inbound/api`
(schema·mapper·router) · `adapter/outbound/gateways`(3어댑터) · `dependencies`.
없는 것: entity(테이블 없음) · orm · orm_mapper · repository.

읽기 방향은 `intent` → `master`·`metric` 단방향. cross-BC 접근은 게이트웨이 안에서만(agent BC의
`RegionFactsGateway` 전례).

## 4. 계약

### 4-1. `POST /intent`

```
요청  { "text": "역삼동에 카페, 예산 5천" }

응답  {
  "intent_type": "A",                 // A 동+업종 · B 동만 · C 동 없음
  "region_code": "1168064000",        // 동이 잡혔을 때
  "region_name": "역삼1동",
  "district_code": "11680",           // 동이 잡혔거나 구만 잡혔을 때
  "industry_id": "cafe",
  "budget_krw": 50000000,
  "missing": ["budget"],              // "region" | "industry" | "budget"
  "candidates": [                     // 동명이동 등 되묻기가 필요할 때만, 아니면 []
    { "region_code": "…", "region_name": "신사동", "district_name": "강남구" },
    …
  ],
  "diagnosis": {                      // A유형에만, 아니면 null
    "type_code": "office",
    "type_name": "낮 인구 우위형",
    "time_label": "day",
    "peak_sales_band": "11_14",
    "sentence": "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다.",
    "year_quarter": "20262"
  },
  "source": "rule"                    // "rule" | "llm" — 어느 경로가 채웠나
}
```

- 실패 응답은 기존 계약 `{ error: { code, message } }`. 빈 문자열은 400 `INTENT_TEXT_EMPTY`.
  파싱 실패는 실패가 아니다 — `intent_type: "C"`, `missing` 셋 전부, 200.
- `GET /intent/myself` — §12 배선 검증. 하드코딩 A유형 응답 왕복.

### 4-2. 착지 URL

`intentToUrl` → `/map?region=1168064000&industry=cafe&budget=50000000`. 없는 값은 생략.

`MapState`에 `budget: number | null`을 더한다. **지금 `serializeMapState`는 상태 필드만
직렬화해서 모르는 파라미터를 첫 상태 변경 때 버린다.** 실어두지 않으면 T3의 예산 프리필이
지도에서 지표 한 번 바꾸는 순간 사라진다.

## 5. 파서 — 규칙이 먼저, LLM은 마지막

### 5-1. 추출기 체인 (Chain of Responsibility)

```
text ─▶ RegionExtractor ─▶ IndustryExtractor ─▶ BudgetExtractor ─▶ (결측 && 잔여 텍스트) ─▶ LlmExtractor
```

각 추출기는 자기 몫만 채우고 다음으로 넘긴다. if/elif가 아니라 리스트다.

**RegionExtractor** — 마스터 `region.name` 427개 + `district.name` 25개. 긴 이름 우선(`달서구`가 `서구`보다
먼저 — 대구의 교훈). 동이 맞으면 `region_code`+`district_code`, 구만 맞으면 `district_code`.
동명이동(`신사동`)은 구 언급이 있으면 그것으로 풀고, 없으면 `candidates`에 둘 다 넣고 `region`을 결측으로 둔다.
사전은 DB에서 1회 로드해 `lru_cache`(대구와 같음).

**IndustryExtractor** — 동의어 사전은 `domain/value_objects/industry_synonyms.py`. 마스터 `industry`
10종에 대해 "카페·커피·디저트 → cafe" 식. 매칭 결과는 반드시 `industry.industry_id`에 있어야 한다.

**BudgetExtractor** — 대구 `_parse_budget` 그대로 이식. `1억 5천` → 150,000,000. 단위 없는 맨숫자는
금액이 아니다(`2층`).

**LlmExtractor** — 앞 셋이 끝난 뒤 **`region`이 결측이고** 텍스트에 한글 잔여가 있을 때만 호출한다
("테헤란로 카페", "홍대 근처"). JSON 모드 1콜, 스키마 `{ region_name: string|null, industry_id:
string|null, budget_krw: int|null }`. **LLM이 준 값은 마스터로 검증한다** — `region_name`이 427개에
없으면 버리고, `industry_id`가 10종에 없으면 버린다. 검증 통과분만 채우고 `source: "llm"`.
호출은 타임아웃 3초, 실패하면 규칙 결과로 응답한다(관문이 LLM 장애로 죽지 않는다).

랜드마크 사전은 두지 않는다. 서울은 수백 개라 규칙으로 못 덮고, LLM이 "홍대 → 서교동"을 안다.
자주 나오는 것은 나중에 `intent_log`가 알려줄 것이다.

### 5-2. 의도 유형

| 유형 | 조건 | 착지 |
|---|---|---|
| A | 동 + 업종 | `/map?region&industry[&budget]` + **diagnosis** |
| B | 동만 | `/map?region[&budget]` — 패널이 동네 프로필을 연다. 업종은 칩으로 되묻는다 |
| C | 동 없음 | `/map[?industry][&budget]` — T2-1(유형 단계구분도)이 생기면 "이 업종이 잘 되는 동네 유형"으로 안내. 그전엔 현재 지도 |

### 5-3. 되묻기

- `region` 결측, `candidates` 있음 → 후보 칩(신사동 둘)
- `region` 결측, `district_code` 있음 → 그 구의 동 칩(15~27개). 구까지 없으면 25구 칩 → 동 칩 2단
- `industry` 결측 → 업종 칩 10 + "잘 몰라요 — 동네부터 볼게요"(B로 착지)
- 칩 선택은 재제출이 아니다. 클라이언트가 응답 객체를 채워 `intentToUrl`로 바로 간다(대구와 같음).
  단, **A가 완성되면 `diagnosis`를 받기 위해 한 번 더 `POST /intent`** 한다 — 텍스트 대신
  `{ region_code, industry_id }`를 보내는 두 번째 형태를 허용한다(파서를 건너뛰고 진단만).

## 6. 한 줄 진단 — 결정론 문장 조립

LLM이 아니다. 어휘 테이블로 조립한다(`apps/agent/domain/value_objects/neighborhood_vocabulary.py`와
같은 사본을 intent가 갖는다 — BC 독립성이 중복 제거보다 우선, `quarter_dimension` 전례).

```
{region_name}은/는 {type_name}이고, {industry_name}은/는 {peak_sales_band 한국어}에 돈이 돕니다.
```

- `type_name` ← `RegionProfileUseCase.find_latest(region_code)`
- `peak_sales_band` ← `RegionIndustryHourGapUseCase.list_bands(region_code, industry_id, quarter)`에서
  **`sales_intensity` 최대 구간**. `gap` 최대가 아니다 — v0.26.0 검증에서 어긋남의 부호는 절대값이
  아니라 상대 순위에 있음이 확인됐다. "언제 돈이 도나"는 매출 강도로 답한다
- 분기: hour_gap은 20254까지, profile은 20262까지다. 각자의 최신을 쓰고 응답에 둘 다 적는다.
  metric BC의 hour_gap 레포지토리에 `latest_quarter(region_code, industry_id)`를 더한다(소규모)
- 조사(은/는)는 받침 규칙 함수 하나로 처리한다
- 유형이 `mixed`면 "뚜렷한 특징이 없는 혼합형이고"로, 상주인구 하한(재건축) 동이면 유형 문장 대신
  근거 문장(`type_reason`)을 그대로 쓴다 — 억지로 유형을 붙이지 않는다(분류 문서 §7-3)
- hour_gap 행이 없는 조합(그 동에 그 업종 매출 없음)이면 뒤 절을 뺀다: "역삼1동은 낮 인구 우위형입니다."

## 7. 프론트엔드

- **랜딩 히어로에 입력창.** 현재 `features/landing/components/landing-page.tsx`(FE v0.15.0)의 히어로
  카피 아래에 폼 + 예시 칩 3 + "지도에서 직접 둘러보기" 링크. 대구 `chat-landing.tsx`의 상태 기계
  (`awaitingRegion`·`awaitingIndustry`)를 우리 어휘로 옮긴다.
- 새 feature `features/intent-gate/` — `api.ts`(`parseIntent`·`diagnose`), `lib/intent-url.ts`(순수,
  테스트), `components/intent-form.tsx`·`clarify-chips.tsx`·`diagnosis-line.tsx`. 랜딩 feature가
  intent-gate를 import하지 않는다 — **랜딩 페이지 조립은 `app/page.tsx`가 한다**(§14 feature 간 직접 import 금지).
- `diagnosis`가 오면 입력창 아래에 한 줄을 띄우고 1.5초 뒤(또는 클릭 즉시) `/map`으로 간다.
  문장을 URL에 싣지 않는다 — 패널이 같은 데이터를 다시 읽는다.
- 예시 칩: "역삼동에 카페, 예산 5천" · "연남동에서 뭘 하면 좋을까" · "홍대 근처 미용실". 세 번째는
  LLM 경로 시연이다.
- mock `/api/mock/intent` — 실 API 미러. 픽스처의 geojson 동 이름 + `INDUSTRY_LABELS` + 예산 정규식으로
  규칙 경로만 흉내 낸다(LLM 경로는 mock에서 "홍대"→서교동 한 건만 하드코딩). `diagnosis`는
  `regionProfileOf`에서 조립.

## 8. 검증

1. 규칙 경로 — 대구 파서 테스트 3종(A·B·C) 이식 + 신사동 되묻기 + `1억 5천` + 맨숫자 무시
2. LLM 검증 — 마스터에 없는 `region_name`을 LLM이 줘도 버려지는가. 타임아웃 시 규칙 응답이 나가는가
3. 진단 — 역삼1동×카페 → "낮 인구 우위형 … 점심(11~14시)". 주거형 동×노래방 → 밤 구간.
   혼합형·재건축 동·hour_gap 없는 조합 세 예외
4. 라우터 — myself · A/B/C 상태 코드 · 빈 텍스트 400 · 두 번째 형태(코드만)
5. 프론트 — `intentToUrl` 순수 테스트, `budget`이 `MapState` 왕복에서 살아남는가, 되묻기 칩 → URL,
   mock 계약
6. 실DB로 예시 칩 셋 다 돌려 `source`와 `diagnosis`를 기록한다

## 9. 범위 밖

- `intent_log` 테이블·분석 (전환 조건: 되묻기 비율을 알고 싶어질 때)
- 상주형 채팅 — 관문형이 먼저. URL 상태라 나중에 얹는다
- C유형의 유형별 안내 — T2-1 뒤
- 예산 프리필 소비 — T3

## 10. 완료 기준

- `POST /intent`가 A·B·C 셋과 `diagnosis`를 §4 계약대로 준다. 규칙 경로는 LLM 없이 돈다
- 랜딩 입력창 → 되묻기 → `/map` 착지가 실 백엔드로 완주한다(E2E 스크립트 1단계 추가)
- `budget`이 지도에서 지표를 바꿔도 URL에 남는다
- `domain/`·`app/use_cases/`에 FastAPI·SQLAlchemy·HTTP 클라이언트 import 없음
- ver_log 백엔드 v0.31.0 · 프론트 v0.18.0
