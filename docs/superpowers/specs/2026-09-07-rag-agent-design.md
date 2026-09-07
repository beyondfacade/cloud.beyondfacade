# RAG + 단일 에이전트 (AI 분석 탭 실구현) — 설계 스펙

> 작성: 2026-09-07 · 전제: `docs/agent-architecture.md`(아키텍처 원칙), `docs/brainstorming.md` §5·§8(응답 규칙·규제 경계), CLAUDE.md
> 범위: agent-architecture.md §3의 "7~8주차 — 단일 에이전트 + 전체 도구 E2E + Hybrid RAG + Recall@5". 오케스트레이터-전문가 분리는 9주차(범위 밖).

---

## 0. 확정된 결정 (2026-09-07 브레인스토밍)

| 항목 | 결정 | 근거 |
|---|---|---|
| 에이전트 두뇌 | **로컬 gemma3:12b 먼저 평가 → Gemini(무료 티어, `GEMINI_API_KEY` 기입됨) 평가 → 비교표로 확정** | 사용자 지정. `LLMGatewayPort` 뒤 어댑터 2종이라 전환 = DI 교체 |
| 임베딩 | **Qwen3-Embedding-4B @ 1536차원** (MRL truncate) — 기본 런타임 **Ollama Q4**(2.5GB, gemma3와 동시 상주 10.6GB < 16GB) | 사용자 지정. com.lifetutorial 검증 전례(Local/Gemini 어댑터, vector(1536) 규격). Gemini `gemini-embedding-001`도 1536 절단 지원 → 스키마 무변경 전환 |
| 색인 운영 | 대량 색인 = **새벽 크론 배치**(기존 04~05시대 수집 크론 뒤), 쿼리 임베딩 = 상주 Ollama 실시간 | 사용자 지정 (LLM 상주·임베딩 1회성 분리) |
| 임베딩 품질 게이트 | Q4 vs fp16(sentence-transformers) 차이는 **Recall@5 하네스 실측으로만 판단** — 유의미할 때만 fp16 재색인 | 추측 금지, 숫자로 결정 |
| 검색 저장소 | pgvector (기존 DB, 확장 활성 확인됨) + cosine + HNSW | 인프라 추가 없음 |

---

## 1. RAG 검색 계층 — `apps/rag` BC (BE v0.19.0)

### 1-1. 테이블 `rag_chunk` (ERD 신규 노드)

| 컬럼 | 타입 | 비고 |
|---|---|---|
| chunk_id | str PK | `{source_type}:{source_id}` (1소스 1청크인 MVP에서 결정적) |
| source_type | str | `funding` \| `news` — StrEnum, if 분기 금지 |
| source_id | str | funding_program.program_id / news_article.article_id (논리 FK) |
| content | text | 임베딩 대상 텍스트 |
| embedding | vector(1536) | HNSW 인덱스 (cosine) |
| embedded_by | str | 모델 식별자 (`qwen3-embedding-4b-q4` 등) — 모델 전환·혼합 오염 감지 |
| published_at / org / url | — | 인용 메타 (응답 규칙 4 — 원문 링크 필수) |
| region_code | str FK nullable | 뉴스가 지역 연결되면 (post-MVP 자리) |

### 1-2. 청킹 (원천이 작아 1소스 1청크)

- **funding** (1,499건): `title + org + field_category + target_text + hashtags + summary` 연결. 마감 지난 공고는 색인 유지하되 검색 시 `is_expired` 조인 필터 (원천 테이블이 진실).
- **news**: `title + description`만 — 본문 미저장(저작권 경계 §5.3) 원칙 유지.
- 재구축: `rebuild --full`로 전량 재생성 멱등 (모델 교체 시). 증분: 미색인 source만.

### 1-3. Port / Adapter (lifetutorial 이식)

- `EmbeddingPort` — `embed_documents(texts)`, `embed_query(text)`.
  - `OllamaQwen3EmbeddingAdapter` (기본): `/api/embed`, `dimensions: 1536` (실검증 완료). 쿼리는 Qwen3 인스트럭션 프리픽스 수동 적용.
  - `GeminiEmbeddingAdapter`: lifetutorial 이식 — 배치 100, **429 재시도 정책 그대로**(전역 공용 풀 원인, 0.5s→4s 지수 백오프, 예산 30s).
  - 선택: `EMBEDDING_PROVIDER` 환경변수 팩토리 (lifetutorial 전례).
- `RagSearchPort` — `search(query_embedding, top_k, source_type?, region_code?) -> list[RagHit]` (pgvector cosine).
- 색인 CLI `build_rag_index.py` (멱등) + 크론 단계(공고 05:10·뉴스 매시 수집 뒤).

### 1-4. Recall@5 평가 하네스

- 평가셋: `data/eval/rag_evalset.jsonl` — `{question, relevant_ids: [...], source_type}`. **초기 50문항: LLM 생성 후보 → 사용자/팀 검수 후 확정** (검수 전 수치는 참고치 표기).
- 하네스 CLI: 평가셋 → Recall@5·MRR 산출, 결과를 `data/eval/results/`에 타임스탬프 JSON — 임베딩 모델·런타임(Q4/fp16/Gemini) 비교 실행 지원.
- 목표: Recall@5 91.5% (프로젝트 목표 지표 — 검색 도구 단위 측정, agent-architecture §3).

---

## 2. 에이전트 루프 — `apps/agent` BC (BE v0.20.0)

### 2-1. LLMGatewayPort

`chat(messages, tools) -> LLMTurn(text | tool_calls, usage)` — 프로바이더 중립 자체 루프 (Tool Runner 미사용: gemma3 로컬과 Gemini 양쪽을 한 계약으로).

- `OllamaLLMAdapter` (gemma3:12b): Ollama chat API tool-call. **도구 호출 JSON 불안정 대비**: 스키마 검증 실패 시 1회 재프롬프트, 그래도 실패 시 해당 도구 스킵+로그 (루프 전체 중단 금지).
- `GeminiLLMAdapter`: function calling. 무료 티어 레이트리밋 → 요청 간 최소 간격 + 429 백오프.
- `llm_usage` 테이블: analysis_id·model·input/output tokens·latency — 에이전트별 비용 가시화 (agent-architecture §4-4, "리포트 1건당 비용" 발표 수치).

### 2-2. 도구 7종 (기존 UseCase 래핑 — Port=Tool 원칙)

| 도구 | 배선 (기존 자산) | SSE 스테이지 |
|---|---|---|
| get_region_metrics | metric BC UseCase (연도별 지표) | market |
| get_region_summary | master region summary | market |
| get_population | population_stat 조회 (신규 얇은 UseCase) | market |
| search_shocks | shock BC 목록 + interest_rate | shock |
| search_news | RAG(news) | shock |
| search_funding | RAG(funding) + 마감 필터 | funding |
| compare_rent_vs_buy | 순수 계산 함수 신규 — rent_price(임대료·공실률) + interest_rate(시설자금 금리) 입력, §8.1③ 산식 | funding |

도구 정의(name/description/input_schema)는 UseCase에서 도출, 스테이지 매핑은 레지스트리 테이블(§5 — if 분기 금지).

### 2-3. SSE — 프론트 기존 계약 그대로 (프론트 수정 최소)

- `POST /analysis` → `{analysis_id}` / `GET /analysis/{id}/events` → SSE.
- 이벤트: `agent_status`(도구의 스테이지 매핑으로 market/shock/funding running/done 방출 — 단일 에이전트지만 UI 3분면 유지), `tool_call`, `report_delta`(섹션 5종: verdict/market/shock/funding/calculator), `report_done`(citations — grade는 정형=fact, RAG=signal).
- 리포트 영속화: `analysis_report` 테이블 (id, 질문 파라미터, 최종 마크다운, citations, 모델, 생성시각) — 데모 재현·평가용.

### 2-4. 시스템 프롬프트 — 응답 규칙 4종 집행 (agent-architecture §2-1 그대로)

외국인 변수 금지 / 지원금 왜곡 보정(2020~2022 폐업률 해석 주의) / 금융 규제 경계(중개 금지·"예상치" 고지) / 신뢰 등급 표기. 규칙 위반은 평가 시나리오의 채점 항목.

## 3. 프론트 전환 (FE v0.13.0)

`use-agent-report.ts`의 `ANALYSIS_API_BASE = "/api/mock"` 상수 제거 → `config.apiBase` 복귀 (TODO 주석이 지정한 그 지점). 계약 동일하므로 그 외 무변경 목표. e2e로 실 스트림 검증.

## 4. 평가 — 두뇌 선정 (로컬 먼저, 외부 다음)

- 시나리오 10케이스 (동×업종 조합 — 데이터 풍부 조합 + 데이터 없는 조합 + 규칙 유발 조합 포함).
- 지표: ①도구 호출 성공률(스키마 준수·필요 도구 커버) ②응답 규칙 준수(위반 0 목표) ③리포트 완성도(5섹션·인용) ④지연시간 ⑤토큰/비용(usage 로깅).
- 실행 순서: **gemma3 전 케이스 → Gemini 전 케이스** → 비교표 → 두뇌 확정 (혼합 배치 — 두뇌/보조 분담 — 도 결과에 따라 옵션).

## 5. 구현 순서·리스크

| 순서 | 산출물 | 버전 |
|---|---|---|
| 1 | rag BC + 색인 + 검색 + Recall@5 하네스 (+평가셋 후보 50) | BE v0.19.0 |
| 2 | agent BC + 도구 7종 + SSE + usage 로깅 (gemma3 배선) | BE v0.20.0 |
| 3 | 프론트 AI 탭 실 API 전환 | FE v0.13.0 |
| 4 | 평가 실행 (gemma3→Gemini) + 비교표 보고 | 문서 |

리스크: gemma3 도구 호출 불안정(→2-1 방어책, 최악 시 Gemini 조기 전환), Gemini 무료 레이트리밋(→평가는 케이스 간 대기, 데모는 사전 워밍), VRAM(Ollama 동시 상주 10.6GB 실측 예정 — 초과 시 keep_alive 조정), 평가셋 검수 병목(→후보 자동 생성 + 검수는 사용자·팀).

## 6. 범위 밖 (명시)

오케스트레이터-전문가 분리(9주차) · 교차 시그널 섹션(post-MVP, 자리만) · 빅카인즈(뉴스는 네이버 기수집분) · EC2 배포(10월, agent-architecture §4) · 대상학년 LLM 구조화 추출.
