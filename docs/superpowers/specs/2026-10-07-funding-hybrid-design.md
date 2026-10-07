# 지원사업 공고 하이브리드 검색 — 규칙으로 자격 거르기 → 질문 유사도로 정렬

> 작성 2026-10-07 · 브랜치 `feat/funding-hybrid` · BE v0.89.0(v0.88.0은 미머지 `feat/load-test`가 선점) · FE v0.64.0
> 사용자 결정(10/7): "하이브리드가 맞다", 리포트와 **지원사업 페이지 둘 다** 적용.

## 1. 왜

- 지금 공고 후보는 **규칙 필터만** 쓴다(`select_candidates`: 서울·전국 ∩ 소상공인·창업 대상 ∩ 미만료, 마감 임박 순). 질문을 무시한다.
- RAG 색인(bge-m3, 공고 1건 = 청크 `funding:{program_id}` 1개, 매일 05:50 증분)은 있지만 **요청 경로에서 읽는 곳이 없다** — v0.68.0(10/5 코드 우선 구조)에서 리포트 도구 루프와 함께 `search_funding` 호출처가 사라졌다.
- 비교 실험(10/7, 평가셋 confirmed 175문항, 개발 DB 읽기 전용, 상위 8건):

| 방식 | Hit@8 (자격 있는 정답 6문항) | MRR@8 | 보여 준 8건 중 자격 밖 공고 |
|---|---|---|---|
| ① 규칙만 (마감 임박 순) | 0/6 | 0.000 | 0% |
| ② RAG만 (전체 색인) | 6/6 | 0.875 | **97.3%** |
| ③ 하이브리드 (규칙 통과 74건 → 질문 유사도) | **6/6** | **0.917** | **0%** |

  RAG만 쓰면 보여 주는 공고 대부분이 마감·타 지역·대상 밖이다. 규칙만 쓰면 질문을 못 찾는다. 하이브리드가 둘 다 지킨다.
  단서: 평가셋(9/15 생성)의 정답 공고 대부분이 지금은 만료·서울 밖이라 적중률 표본은 6문항뿐이다. 결정 근거는 "자격 밖 노출 97% vs 0%"다. 스크립트: `scripts/compare_funding_hybrid.py`(개발 DB 읽기 전용 · 로컬 Ollama).

## 2. 동작

1. 규칙 필터는 **그대로** 먼저 돈다(자격·구 전용 제외 — 정답의 경계).
2. 질문(`q`)이 있으면, 규칙을 통과한 **전체** 후보를 질문과의 코사인 거리로 정렬한다(색인된 공고 = `rag_chunk.embedding`). 색인이 아직 없는 새 공고는 정렬된 것 **뒤에 규칙 순서대로** 붙인다(빠뜨리지 않는다).
3. 질문이 없으면 지금과 **똑같다**(마감 임박 순).
4. 임베딩이 실패하면(Ollama 다운·타임아웃) 규칙 순서로 돌려주고 응답에 그 사실을 표시한다 — 리포트·화면이 멈추지 않는다. 경고 로그 1줄.
5. `q`는 앞뒤 공백을 자르고, 비면 없는 것으로 본다. 200자를 넘으면 **422가 아니라 200자에서 자른다**(자유 입력이라 거절보다 관대하게).

## 3. API 계약 (실 API = mock 미러, CLAUDE.md §15)

### `GET /funding/candidates?industry=&need=&stage=&region=&q=`
기존 응답에 필드 하나 추가:
```jsonc
{ "candidates": [...], "industry_id": ..., "external_funding_need": ..., "stage": ..., "disclaimer": ...,
  "order": "relevance" | "deadline" }   // q가 있고 정렬 성공 = relevance, 그 외 = deadline
```

### `GET /funding/support?region=&industry=&q=`
기존 응답(loans·district·others·rates…)에 필드 하나 추가 — 세 묶음은 **그대로**:
```jsonc
{ ..., "search": null }                                  // q 없음
{ ..., "search": { "query": "인테리어 비용",           // 자른 뒤의 q
                   "available": true,                    // false = 임베딩 실패(이때 items는 빈 배열)
                   "items": [SupportItem, ...] } }       // 최대 8건, 질문과 가까운 순
```
- `items`의 자격 경계는 세 묶음을 나누기 전의 후보 목록과 같다(`build_support_guide`의 `items` = 규칙 통과 ∩ `open_to_district`). 묶음 구분 없이 질문과 가까운 순으로 8건.
- 검색 실패 시 규칙 순서로 채우지 **않는다** — "검색 결과"라고 보여 주면서 마감 순을 내면 거짓이다. 화면은 "지금은 검색을 쓸 수 없어요"를 보여 준다.

### 리포트 (`POST /analysis` → SSE)
- 분석에 질문이 있으면 `facts.funding_candidates`를 `q=질문`으로 고른다. 배열 계약은 그대로(프론트 변경 없음).
- 리포트 지원사업 절(코드가 쓰는 `report_sections._funding`)은 질문으로 정렬됐을 때 첫 줄에 "질문과 가까운 순으로 골랐습니다." 한 문장을 붙인다. 순서 정보는 사실 묶음 키 `funding_order`("relevance"|"deadline")로 넘긴다(facts 계약 키 추가 — 프론트는 모르는 키를 무시한다).

## 4. 백엔드 구조 (헥사고날)

| 층 | 무엇 |
|---|---|
| rag BC — input port | `RagSearchUseCase.rank_within(query: str, chunk_ids: list[str]) -> list[str]` — 주어진 청크만 질문과 가까운 순으로(색인 없는 id는 결과에 없음) |
| rag BC — output port·repo | `RagRepositoryPort.rank_within(embedding, chunk_ids) -> list[str]` — `chunk_id = ANY(:ids) AND embedding IS NOT NULL ORDER BY embedding <=> :v` |
| funding BC — output port (ISP) | `QuestionRankerPort.rank(question: str, program_ids: list[str]) -> list[str]` — 실패 시 예외 |
| funding BC — gateway (ACL, cross-BC) | `RagQuestionRankerGateway` — `funding:{id}` 접두로 rag BC 호출, 결과를 program_id로 되돌림 |
| funding BC — domain service | `order_by_relevance(candidates, ranked_ids)` — 순수 함수: 정렬된 것 + 나머지 규칙 순서 (테스트 대상) |
| funding interactor | `list_candidates(..., question=None)` · `support_guide(..., question=None)` — 랭커 실패 → deadline / `available: false` |
| agent BC | `FundingFactsPort.candidates(..., region_code, question=None)`, `ReportFactsCollector._funding`이 질문을 넘기고 `funding_order`를 facts에 싣는다 |
| 배선 | `funding_dependencies`에 랭커 주입(rag `get_rag_search_use_case("bge-m3")`) |

- `if q:` 분기는 인터랙터의 입력 유무 판단 한 곳만 — 순서 정책은 도메인 함수가 갖는다.
- 성능: 질문 1건당 임베딩 1회(로컬 GPU 약 0.1~0.3초) + 벡터 정렬 1쿼리(후보 수십 건). 질문 없는 요청은 비용 0.

## 5. 프론트 (Codex 위임)

- `shared/api/types.ts`: `FundingCandidateList.order`, `SupportGuide.search: SupportSearch | null`, `SupportSearch {query, available, items}`.
- mock(`app/api/mock/funding/support`, `candidates`): `q`를 받아 결정적 정렬(문자열 포함 점수 + FNV-1a 동률 해소, `Math.random` 금지), 계약 테스트.
- 지원사업 페이지(`features/support`): 상단에 검색 입력("찾는 지원을 적어 보세요 — 예: 인테리어 비용, 청년 대출") → `q`로 재조회. 결과 절 "질문과 가까운 공고"를 세 묶음 위에 둔다. `available=false`면 안내 문구. 빈 결과면 "맞는 공고를 찾지 못했어요". 자격 확정이 아니라는 기존 고지 유지. 토큰 기반 스타일·다크모드(§16).
- queryKey: `["support", region, industry, q]`.

## 6. 검증

- 백엔드 TDD: 도메인 정렬 함수(정렬+미색인 뒤붙임), 인터랙터(질문 있음/없음/랭커 실패), 라우터 계약(`order`, `search` null/available), rag repo `rank_within`(테스트 DB), 리포트 facts `funding_order`·지원 절 문장.
- 실제 확인: 8201에서 `/funding/support?q=인테리어` · `/funding/candidates?q=청년 대출`, 질문 있는 리포트 1건(지원사업 절 순서·문장), Ollama 끈 상태에서 deadline·`available:false`.
- 비교 실험 재현: `backend/.venv/bin/python scripts/compare_funding_hybrid.py` (결과는 위 표). 평가셋을 현재 자격 공고로 보강하는 일은 후속.

## 7. 개정 1 (10/7 오전) — 유사도 기준선 + 더보기

미리보기에서 "인테리어 비용"이 관련 없는 공고 8건으로 채워졌다(자격 통과 공고 중 인테리어 공고가 없는데 무조건 8칸을 채움). 실측(질문 8개 × 자격 통과 74건, bge-m3 코사인 거리)으로 기준선을 정했다.

- **기준선:** 거리 `d ≤ min(0.54, 1등 거리 + 0.08)`인 공고만 "질문과 관련 있음". 짧고 일반적인 질문은 전체가 가깝게(중앙값 0.50), 구체적인 질문은 1등만 가깝게 나와 절대값 하나로는 못 가른다 → 절대 상한 + 1등과의 차이.
  - 실측: 고용보험료 지원 1건(0.329) · 폐업 후 재창업 3건 · 온라인 판로 2건 · 수출 해외 진출 4건 · 임대료 부담 1건(경영안정 바우처 0.537) · 인테리어 비용 1건(LED간판 0.531) · 평가셋 자격 정답 6문항 **6건 모두 기준 안**(문항당 1~4건 남음).
  - 정책은 funding 도메인 순수 함수(`relevant_ids(scored, max_distance=0.54, max_gap=0.08)`), 포트는 거리까지 돌려준다: `QuestionRankerPort.rank(question, program_ids) -> list[tuple[str, float]]`(가까운 순, 색인 없는 id 없음), rag `rank_within`도 `(chunk_id, distance)`.
- **지원사업 검색 `search.items`:** 기준선을 통과한 공고 **전부**(가까운 순, 8건 상한 없음). 하나도 없으면 빈 배열("맞는 공고를 찾지 못했어요"). 색인 없는 새 공고는 관련도를 모르므로 검색 결과에 넣지 않는다.
- **후보 `/funding/candidates`(리포트):** 기준선 통과 공고를 앞에, 나머지는 규칙 순서로 뒤에 — 8건은 그대로 채운다. 통과 공고가 **하나도 없으면 `order: "deadline"`**(아무것도 재정렬되지 않았으니 "질문과 가까운 순" 문장을 붙이지 않는다).
- **프론트 더보기:** 검색 결과는 처음 8건, 하단 "더보기 (n건 더)" 버튼으로 8건씩 더 펼친다. 결과 절에 "관련 공고 N건" 표시. 다른 세 묶음은 그대로.
- **소담스퀘어 지역 공고(강원·전남 등) 확인 결과:** 원천이 17개 시도 전체 태그 + 신청 대상 "소상공인"(지역 제한 문구 없음) → 규칙상 전국 공고가 맞다. 필터 결함 아님(사용자 결정 대기: 그대로 / 지역 표기 공고 뒤로 보내기).
- **구현 확인(10/7 10:20, 미리보기 8203·3203):** 인테리어 비용 0건("찾지 못했어요") · 고용보험료 지원 1건 · 온라인 판로 2건 · **카페 창업 자금 20건**(짧고 일반적인 질문은 자격 통과 공고 전체가 비슷한 거리라 기준선이 거의 거르지 못한다 — 더보기로 받는다. 남는 한계). 모바일 390px에서 더보기 8 → 16 → 20건, 다 펼치면 버튼 숨김 확인.
