# 조달·준비 — 조정한 계획을 들고 상담에 간다

> 작성 2026-09-23 · 브랜치 `feat/funding-prep` · 백엔드 v0.34.0~ / 프론트 v0.23.0~
> 선행: `specs/2026-09-23-finance-plan-design.md`(T3 — 최초안/현재안, `external_funding_need`)
> 참조: 대구 `docs/2026-09-18-imbank-consultation-plan.md` §0 공통 제약, `apps/consultation`(assumptions·open_questions)
> 우리 자산: `funding` BC(기업마당 2,032건, `hashtags`·`target_text` 원문 보존), RAG `search_funding` 도구, ECOS 금리

## 1. 목적 — "무엇을 물어볼지"가 결과물이다

T3의 헤드라인은 "자기자본 외 조달 필요 3,160만 원"이다. 그 다음 질문은 "어디서, 어떻게"인데, 대구가
기록한 함정을 그대로 피한다 — **위험 진단 → 곧바로 대출 상품**이 아니다. 결과물은 상품 목록이 아니라
**조정한 계획 + 후보 + 확인할 질문**을 담은 상담 준비자료다. 은행 전송·예약·신청은 구현하지 않고 그렇게
보이게도 하지 않는다(대구 §0 "제휴 없음·공개 채널 안내").

우리와 대구의 차이: 대구는 iM뱅크 상품 12건을 수기로 정본화했다. 우리는 **서울 상품 정본이 없다**
(`api.md` — 서울신보 스크래핑 P3, 은행연합회 API 없음). 그래서 이번 범위의 "후보"는 **정책자금 공고
(기업마당)**와 **공시 금리(ECOS)**로 한정하고, 서울신보·금감원 공시는 T4-3 별도 조사로 둔다.
후보가 얇은 대신 **질문을 두껍게** 한다 — 그게 상담에서 실제로 쓰이는 것이다.

## 2. 어디에 둘 것인가

새 BC를 만들지 않는다. 세 조각이 각자 있는 BC에 붙는다.

| 조각 | BC | 이유 |
|---|---|---|
| 후보 공고 필터 | `funding` | 이미 있는 테이블·라우터. 조회 유스케이스에 필터 메서드 추가 |
| 확인할 질문 생성 | `finance` | 계획(13필드·결과)에서 결정론으로 만든다 — 계획을 아는 BC |
| 준비자료 조립·Markdown | 프론트 `features/plan` | 화면 상태(`sessionStorage` 초안)가 재료의 정본이다. 서버 테이블 없음 |
| 리포트 `funding` 절 | `agent` | 기존 5섹션의 `funding`이 후보·질문을 읽어 설명한다 |

상담 세션 테이블(대구 4테이블)은 **만들지 않는다.** 로그인이 없다. `sessionStorage` 초안이 정본이고
Markdown 내보내기가 저장이다.

## 3. 후보 공고 — `GET /funding/candidates?industry=&need=&stage=`

`funding` BC 유스케이스에 `list_candidates(industry_id, external_funding_need, stage)` 추가.
결정론 필터, LLM 없음.

- 미만료(`is_expired = false`, `deadline` 없거나 오늘 이후)
- **지역 — `hashtags`로 판정한다**(쉼표 구분 태그, 앞쪽에 분야·시도 태그가 온다). 2026-09-23 실측:
  · `서울` 태그가 있고 17개 시도가 전부 있진 않음 → **서울 전용**(73건)
  · 17개 시도 전부 또는 `전국` 태그 → **전국**(45건). 전국 공고는 "시도 언급 없음"이 아니라 17개를 다 단다
  · 그 외 → 타 시도, 제외(1,359건)
  · **소관기관(`org`)이 서울 밖 지자체**(`…시/군/구/광역시/특별자치도/도`로 끝나고 서울·서울 자치구가
    아님)면 태그와 무관하게 제외 — 과천시 이자차액보전처럼 17개 시도를 다 달아둔 지자체 공고가 26건
    걸린다. 서울 자치구 25개는 `district` 마스터로 판정
  · 규칙은 `funding/domain/services/region_filter.py`에 시도명 17개 사전 + 위 판정으로. 오탐이 나면
    사전과 접미사 목록만 고친다
- 대상: `target_text`에 "소상공인"·"창업"·"예비창업" 중 하나 — `stage`가 `pre`(사업자등록 전)면
  "예비창업"·"창업" 가중, `registered`면 "소상공인" 가중
- 분야: `field_category` in (`금융`, `창업`, `경영`) 우선, 나머지는 뒤
- 정렬: 서울 전용 → 전국 순, 그 안에서 마감 임박 순(상시는 뒤), 상위 **8건**. 실측 풀은 92건(소상공인·창업 ∩ 서울/전국 − 서울 밖 지자체), 금융·창업·경영 60건. 각 항목에 `why`(어느 규칙에 걸렸는지 한 줄 — "서울·소상공인·금융")
- 응답: 기존 `FundingProgramResponse` + `why`. 원문 링크 필수(엔티티 규칙 그대로)

`external_funding_need`는 이번엔 **필터에 쓰지 않는다** — 공고에 한도가 구조화돼 있지 않다. 응답에
그대로 되돌려 화면이 "조달 필요 3,160만 원 기준 후보"라고만 쓴다. 한도 구조화는 T4-3.

## 4. 확인할 질문 — `POST /finance/questions`

요청 = T3 계획 초안 요약 `{ input: FinanceInput, result: FinanceResult, unconfirmed: string[],
profile: { business_registered: bool|null, planned_opening_date, funds_needed_by, guarantee_status,
policy_confirmation_status }, change_reason }`. 응답 `{ questions: [{ text, basis, kind }] }`.

**결정론 규칙 목록**(Chain of Responsibility — 규칙 객체 리스트, 각자 해당할 때만 질문을 낸다).
대구가 `assumptions`·`open_questions`로 나눈 것을 `kind: "gap" | "assumption" | "procedure"`로 잇는다.

| 조건 | 질문 | kind |
|---|---|---|
| `external_funding_need > 0` | "자기자본 외 {n}만 원을 어떤 경로(보증·대출·정책자금)로 나눠 조달할 수 있는지" | gap |
| `funding_gap > 0` | "희망대출 {m}만 원이 승인돼도 {k}만 원이 남습니다. 추가 조달 또는 비용 축소 중 무엇이 현실적인지" | gap |
| `desired_loan > 0` | "희망대출 {m}만 원의 예상 금리·기간·상환 방식. 계산은 공시 평균 {r}%로 했습니다" | assumption |
| 시나리오 비관에서 런웨이 < 6개월 | "매출이 기준의 60%일 때 {x}개월 버팁니다. 그 경우 대비책을 상담에서 물어볼지" | assumption |
| `unconfirmed`에 금액 필드 | "{필드}는 아직 확인하지 않은 값입니다(0원 아님). 견적을 받아야 하는지" | assumption |
| 월매출이 실측 프리필 그대로 | "예상 월매출 {v}만 원은 이 동 {업종} 평균입니다. 신규 점포 기준으로 낮춰 잡아야 하는지" | assumption |
| 임대료가 권역 근사 그대로 | "월세는 {권역} 평균 기준입니다. 실제 매물 조건으로 다시 계산해야 하는지" | assumption |
| `business_registered` null | "사업자등록 전인지 후인지에 따라 지원 대상이 달라집니다 — 어느 쪽인지" | procedure |
| `guarantee_status == "unknown"` | "보증기관(서울신보) 보증서 발급 절차와 소요 기간" | procedure |
| `policy_confirmation_status == "unknown"` | "소진공 정책자금 확인서가 필요한지, 필요하다면 발급 절차" | procedure |
| 후보 공고가 있음 | "{공고 제목}에 해당하는지, 은행 대출과 병행 가능한지" (상위 3건) | procedure |

**질문은 사용자가 편집·삭제·추가한다.** 서버는 초안을 줄 뿐이다. 근거(`basis`)는 어느 수치에서 나왔는지
한 줄("조달 필요 31,600,000원 > 0").

## 5. 프론트 — `/plan`의 ⑤ 단계

T3의 `/plan` 흐름 끝에 붙는다: 비교·선택 → **"조달·상담 준비 →"** →

```
① 창업 단계 확인   사업자등록 여부 · 개업 예정일 · 자금 필요일 · 보증/확인서 진행 상태
                  (대구 consultation-profile-form 이식 — "모름"을 0·아니오로 바꾸지 않는다)
② 후보 공고        GET /funding/candidates — 카드 8장(제목·기관·기간·why·원문 링크). "자격 확정이 아니다" 고지
③ 확인할 질문      POST /finance/questions — 목록, 편집·삭제·추가, 순서 변경
④ 준비자료         한 화면: 선택한 계획(입력 13 + 결과 네 갈래) · 최초안/현재안 비교 · 변경 이유
                  · 후보 공고 · 확인할 질문 · 가정·단서(프리필 caveat 전부)
                  [Markdown 복사] [인쇄]  — 저장은 사용자 몫. 은행 전송 버튼 없음
```

- `sessionStorage` 초안(`beyondfacade.plan.v1`)에 `profile`·`questions`(편집본)·`candidates_seen` 추가.
- Markdown 조립은 순수 함수 `lib/prep-markdown.ts`(테스트). 숫자는 서버 결과를 그대로 쓴다.
- **"충분합니다"·"승인"·"신청 완료" 문구 금지**를 테스트로 고정(문자열 스캔).

## 6. 리포트 `funding` 절이 같은 재료를 읽는다

agent 도구 `search_funding`(RAG)은 그대로 두고, **`get_funding_candidates`** 도구를 더한다 — §3과 같은
결정론 필터를 호출(cross-BC 게이트웨이). `funding` 절 프롬프트 계약: "후보는 자격 확정이 아니라고
쓴다. 금리·한도는 예상치라고 고지한다(기존 규칙 ③). 확인할 질문이 있으면 그 절에 그대로 인용한다".
`finance` 도구(T3-3)의 결과가 있으면 `external_funding_need`를 헤드라인으로 삼는다.

## 7. 검증

1. 후보 필터 — 서울/전국만 남고 타 시도 제외(사전 17개), 마감 임박 순, 상시 뒤, `why` 규칙명 정확
2. 질문 규칙 — 11개 규칙 각각 해당/비해당 1쌍, 대구 시연 사례(조달 3,160만·부족 660만)에서 gap 질문 2개
3. 문구 금지 — `/plan`·준비자료·리포트 프롬프트에 "충분합니다"·"신청 완료" 없음
4. Markdown — 숫자가 서버 결과와 같고 caveat가 전부 실려 있는가
5. 실 백엔드 E2E `[10]` — `/plan` 계산 → 조달·준비 → 후보 ≥1 · 질문 ≥3 · Markdown에 조달 필요 금액

## 8. 범위 밖 → T4-3 별도 조사

- 서울신보 보증상품·금감원 "금융상품 한눈에" 은행 공시 — 정본화 후 후보에 합류
- 공고 한도·금리 구조화(`external_funding_need`로 필터)
- 상담 세션 서버 저장·PDF

## 9. 완료 기준

- 계획 → 후보 8건 이내 + 질문 초안 → 편집 → Markdown 복사가 실 백엔드로 완주한다
- 후보에 타 시도 한정 공고가 섞이지 않는다
- 준비자료 어디에도 확정·승인을 뜻하는 문구가 없다
- ver_log 백엔드 v0.34.0 · 프론트 v0.23.0
