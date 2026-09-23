# 채팅 관문 전환 로드맵 — 태스크 재구성

> 작성 2026-09-23 · 기준: `codex/seoul-atlas-landing` `cc29fa1` (BE v0.30.0 / FE v0.16.0) + 미커밋 랜딩 25파일
> 방향 근거: 세션 브레인스토밍(대구 `cloud.localhostdaegu` 관문 구조 참조). 상세 설계서는 그룹별로 T1-0·T3-0에서 쓴다.
> 관련: `specs/2026-09-23-map-metric-contract.md` · `specs/2026-09-23-region-profile-design.md`

## 0. 척추

```
⓪ 관문      입력창 하나 → POST /intent (규칙 먼저, 자유문·랜드마크만 LLM)
① 한 줄 진단  동네 유형 + 시간대 + 업종 어긋남 한 문장            ← 우리만 할 수 있는 단계
② 무대       /map?region&industry&budget — 동 선택 상태로 착지, 패널 서사
③ 계획       /plan — 재무 엔진(대구 engine.py 이식). 월매출은 실측 프리필
④ 조달·준비   조달 필요액 → 기업마당·금리 후보 → "확인할 질문" → 상담 준비자료
⑤ AI 리포트   기존 5섹션이 ③④를 흡수
```

중심은 ①②(상권 분석). ③④는 방향성이다. 대구가 기록한 함정 셋을 그대로 피한다 —
위험 진단→곧바로 대출 상품 금지 · 부족액 0원 함정 · 재무 입력 없는 리포트 금지.

## 1. 작업 방식

- **태스크 그룹 = 브랜치.** T0로 `main`에 합친 뒤 `feat/intent-gate` · `feat/map-stage` · `feat/finance`. 병렬 그룹은 워크트리.
- **그룹당 설계서 하나** → 계획 → TDD 구현 → 커밋 → ver_log. 태스크마다 설계서를 쓰지 않는다.
- **부분 스테이징 금지.** 작업 트리는 항상 깨끗하게. 다른 세션의 미커밋을 발견하면 그것부터 착지시킨다.
- 빨간 테스트를 커밋하지 않는다.

## 2. 태스크

버전: 백엔드 v0.31~, 프론트 v0.18~ (T0-2 병합에서 프론트를 v0.17.0까지 재번호했다).

### T0 — 합치기 (전부의 선행, 순서 고정)

| # | 할 일 | 상태 |
|---|---|---|
| T0-1 | 랜딩 25파일 커밋. vitest 실패 1건(`use-agent-report.test.ts`)은 랜딩의 실 API 전환에 맞게 테스트를 고친다 | |
| T0-2 | `feature/analysis-api` 병합 — 충돌 8파일(`main.py`·`env.py`·`analysis_interactor.py`·`map-state.ts`·`map-view.tsx`·`side-panel.tsx`·ver_log 둘, 전부 양쪽 추가형). alembic `merge`로 head 둘(`b2c3d4e5f6a7`+`a4e7b2c9d813`) 통합. **프론트 ver_log 번호 충돌 정리**(양쪽이 v0.14.0·v0.14.1을 각자 씀) | |
| T0-3 | `main` 병합 · 푸시 · 8201 재기동 · 도커 이미지 갱신 | |
| T0-4 | `docs/erd.md` §6에 새 테이블 13개 반영 | |

### T1 — 관문 (`intent` BC · 랜딩 히어로)

| # | 할 일 |
|---|---|
| T1-0 | 설계서 `specs/2026-09-2x-chat-first-direction.md` — 척추, 파서 계약, 응답 `{intent_type, region_code, industry_id, budget_krw, missing, diagnosis}`, LLM 포트 배치 |
| T1-1 | `apps/intent` — myself → 규칙 파서(동·구 이름은 `region` DB, 업종 동의어, 예산 정규식) → LLM 폴백(랜드마크·자유문만) |
| T1-2 | 랜딩 히어로 입력창 + 예시 칩 + 되묻기 칩 + `intentToUrl` → `/map` 착지. mock `/api/mock/intent` |
| T1-3 | 한 줄 진단 `diagnosis` — `/profiles` + hour_gap. hour_gap 조회 포트는 T2-4와 공유(먼저 하는 쪽이 만든다) |

### T2 — 무대

| # | 할 일 |
|---|---|
| T2-1 | 유형 단계구분도 — `GET /profiles/types` + 범주 팔레트 6색(주거형 가장 옅게) + 범주 범례 + 기본 지표를 유형으로 |
| T2-2 | 컨트롤바 두 무리(동네/업종) + 시간 셀렉터 분기(연/분기) |
| T2-3 | 패널 서사 재배열 + "얼마나 버티나"(`GET /commerce-changes/{region}` 상세 계약, 영업/폐업 개월·상권변화 배지) |
| T2-4 | 시간대 어긋남 — `GET /hour-gaps` 라우터(상세 계약) + 유동·매출 두 선 SVG. **gap 하나만 그리지 않는다** |
| T2-5 | 리포트 `market`에 비교 기준 주입(`seoul_commerce_change_baseline`·유형별 중앙값) |

### T3 — 계획 (`finance` BC · `/plan`)

| # | 할 일 |
|---|---|
| T3-0 | 설계서 — 엔진 이식 계약, 프리필 원천(월매출 = `sales ÷ store ÷ 3` 실측+편차 단서 · 예산 = 관문 · 월세 = 자치구 근사) |
| T3-1 | `apps/finance` — 대구 `engine.py` 이식 + `POST /finance/simulate` + `GET /finance/prefill?region&industry` |
| T3-2 | `/plan` — 프리필 확인 폼 → 네 갈래 결과 → 최초안/현재안 비교 → 변경 이유. `sessionStorage` |
| T3-3 | agent `calculator`가 finance 도구를 읽게 — `compare_rent_vs_buy` 흡수 |

### T4 — 조달·준비

| # | 할 일 |
|---|---|
| T4-1 | 조달 필요액 → `funding_program` + ECOS 금리 → "확인할 질문". 상품 매칭이 아니다 |
| T4-2 | 상담 준비자료 Markdown 저장·인쇄 |
| T4-3 | (별도 조사) 서울신보·금감원 공시 상품 정본 |

### T5 — 운영·부채 (HANDOFF 승계)

fp16 재색인 · RAG 평가셋 검수 · SGIS 키 · 카탈로그 전환 조건 감시(`map-metric-contract` §6).

## 3. 의존

```
T0 ──┬── T1 ────┐
     │          ├── T3 ── T4
     └── T2 ────┘
     T1-3 ↔ T2-4 : hour_gap 조회 포트 공유
```

T1·T2 독립. 권장 순서 T1-1·T1-2 → T2-4 → T1-3 → 나머지 T2 → T3 → T4.
