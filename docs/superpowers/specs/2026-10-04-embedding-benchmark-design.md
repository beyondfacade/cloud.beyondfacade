# 임베딩 모델 평가 — 로컬용·API용 각 1종 선정 (2026-10-04)

> 요구사항정의서 #4(고객요구 사항) "검색 임베딩 모델 평가"의 구현 설계.
> 참고 실험: research.remakeday.com/experiments/model-selection (bge-m3@1024 로컬, gemini-001@2560 제출 채택. 검수 골든 22문장 기준).

## 1. 현황

| 항목 | 값 |
|---|---|
| 운영 검색 임베더 | qwen3-embedding:4b — 색인 fp16(sentence-transformers) / 질의 Ollama Q4, MRL 1536 |
| 저장 | `rag_chunk.embedding` `Vector(1536)` + HNSW, pgvector 0.8.5 |
| 코퍼스 | 8,891청크 (funding 2,265 · 평균 427자 / news 6,626 · 평균 157자) |
| 평가셋 | `data/eval/rag_evalset.jsonl` confirmed 180 (funding 140 · news 40), rejected 20 |
| 현 성적 | fp16 Hit@5 1.000 · MRR 0.946 / ollama 1.000 · 0.942 — **상한, 모델 변별 불가** |
| 장비 | RTX 5060 Ti 16GB. Ollama에 `bge-m3`, `qwen3-embedding:4b`, `gemma4:12b` 설치됨 |

## 2. 결정

1. **로컬용 1종, API용 1종을 각각 고른다.** 로컬 1위가 현 운영 구성보다 유의하게 낫지 않으면 교체하지 않는다.
2. **측정 대상은 9개 조합으로 고정**한다(추가 후보 없음).

   | 구분 | 모델 | 차원 | 구성 |
   |---|---|---|---|
   | 로컬 | bge-m3 | 1024 | Ollama 기본(F16), 색인·질의 동일, instruction 없음 |
   | 로컬 | qwen3-embedding-4b | 1536, 2560 | 운영 그대로 — 색인 fp16 / 질의 Ollama Q4 + `QUERY_PROMPT` |
   | API | gemini-embedding-001 | 1024, 1536, 2560 | `task_type` RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY |
   | API | gemini-embedding-2 | 1024, 1536, 2560 | 001과 같은 방식(§9-1 확인) |

3. **오프라인 벡터 캐시 + numpy 전수 검색**으로 잰다. 운영 DB는 건드리지 않는다. HNSW 근사 오차를 배제해 임베딩 품질만 비교한다. 채택 모델의 운영 반영(스키마·재색인)은 별도 작업.
4. **모델당 1회만 임베딩**한다. MRL 모델은 최대 차원(Gemini 3072, qwen 2560)으로 받아 앞부분을 잘라 L2 재정규화해 하위 차원을 만든다. bge-m3는 1024 고정.
5. **평가셋 = 기존 confirmed 180 + 어려운 질문 약 60.** 어려운 질문은 따로도 집계한다.

## 3. 어려운 질문 (`subset: "hard"`)

| `hard_kind` | 원천 | 건수 | 질문 조건 |
|---|---|---|---|
| `colloquial` | funding | 20 | 공고명·본문 핵심어를 쓰지 않은 창업자 말투 |
| `sibling` | funding | 20 | 같은 시·유사 공고 쌍에서 정답 공고에만 해당하는 조건으로 구별 |
| `news_event` | news | 20 | 헤드라인 단어를 피해 사건 내용으로 질문, 같은 사건 기사는 모두 `relevant_ids` |

- **모델 중립 선정.** 유사 공고 쌍은 지역 일치 + 제목 토큰 Jaccard 같은 메타데이터로만 고른다. 어떤 임베딩 모델도 표본 선정에 쓰지 않는다(특정 모델 쪽으로 기우는 것 방지).
- 표본 추출은 기존 규칙 그대로 결정적(chunk_id 오름차순, 기존 행 건너뜀). funding은 미만료 공고만.
- 흐름: `generate_evalset --provider claude --mode hard --hard-kind ...`(Strategy 추가) → `judge_evalset`(Claude 1차) → `review_evalset sheet/apply`(사용자 검수). 판정 기준은 기존과 동일 — 질문만 보고 유사 공고보다 우선해 정답이면 O.
- jsonl 스키마 확장: 선택 필드 `subset`, `hard_kind`. 없으면 기존 행(`subset` = base)으로 본다. 기존 CLI는 모르는 키를 무시해야 한다(회귀 테스트).
- 기존 180건은 qwen 시절에 검수돼 qwen 쪽으로 기울었을 수 있다. 보고서에 이 한계를 적는다.

## 4. 코퍼스 스냅샷

- `rag_chunk` 전량(만료 공고 포함)을 `chunk_id, source_type, content`로 jsonl에 고정하고 sha256을 기록한다. 9개 조합이 같은 텍스트를 임베딩한다는 보장이다.
- 만료 공고를 빼지 않는 이유: 9/24 이후 만료된 confirmed 정답이 사라지면 문항이 무효가 된다. 만료 공고는 모델 중립적인 방해 문서로 남는다. 운영 필터와의 차이는 보고서에 적는다. → F16(10/4 `ollama show bge-m3` 확인).

## 5. 구성 요소

### 5-1. 임베딩 어댑터 (`apps/rag/adapter/outbound/embeddings/`)
- 기존 3종(`Fp16Qwen3EmbeddingAdapter`, `OllamaQwen3EmbeddingAdapter`, `GeminiEmbeddingAdapter`)에 생성자 인자 `dim`을 추가한다. 기본값은 현재 값(1536)이라 운영 동작은 바뀌지 않는다.
- `GeminiEmbeddingAdapter`에 `model` 인자(기본 `gemini-embedding-001`)를 추가한다. `model_name`도 이 값을 따른다.
- 신규 `OllamaBgeM3EmbeddingAdapter` — `EmbeddingPort` 구현, `bge-m3`, 1024, 질의·문서에 프리픽스 없음, L2 정규화.
- `rag_dependencies` 운영 레지스트리는 바꾸지 않는다. 벤치마크는 자기 레지스트리(조합 이름 → 어댑터 생성 함수, dict 디스패치)를 쓴다.

### 5-2. 벤치마크 CLI — `apps/rag/adapter/inbound/cli/benchmark_embeddings.py`
| 하위 명령 | 하는 일 |
|---|---|
| `snapshot` | §4 코퍼스 jsonl + sha256 |
| `embed --model {bge-m3,qwen3,gemini-001,gemini-2}` | 문서 벡터를 최대 차원으로 `.npy` 캐시. 배치 단위로 저장해 중단 후 이어서 실행 가능. 질의 벡터(평가셋 전 문항)도 같이 캐시 |
| `evaluate` | 조합별 절단·재정규화 → 코사인 전수 검색 → 지표·bootstrap → `results.json`, `report.md` |
| `latency --model ...` | 질의 240건 × 3회 실측 p50/p95. 로컬은 `gemma4:12b`와 동시 상주 확인(`ollama ps` + nvidia-smi) |

- qwen 문서 벡터는 fp16 어댑터, 질의 벡터는 Ollama Q4 어댑터로 만든다(운영 혼용 구도 재현).
- 순수 로직(절단·정규화·전수 검색·지표·bootstrap)은 프레임워크 없는 모듈로 분리해 단위 테스트한다.

### 5-3. 지표 (기존 `evaluate_rag.py`의 `hit_at_k`, `mrr` 재사용)
- 추가: `top1`(= Hit@1), `ndcg_at_k`(이진 관련도, 동치 집합 내 여러 적중 허용), `paired_bootstrap_ci(a, b, n=10000, seed=0)` — 문항별 점수 차이의 95% 구간.
- 집계 단위: 전체 / `subset`(base·hard) / `source_type` / `hard_kind`.

## 6. 판정 규칙

- **주 지표: 전체 문항 MRR.** 정답이 동치 집합이라 MRR이 맞다. top-1·Hit@5·nDCG@10·hard MRR은 표에 함께 싣는다.
- **동률:** 1위와 후보의 MRR 차이 bootstrap 95% 구간이 0을 포함하면 동률. 동률이면 낮은 차원 → 짧은 질의 지연 순으로 고른다.
- **로컬:** 기준선 qwen@1536(운영 구성). 1위가 기준선보다 유의하게 낫지 않으면 현행 유지. 하드 게이트 ① `gemma4:12b`와 동시 상주 시 모델이 밀려나지 않음 ② 질의 임베딩 p95 ≤ 500ms(기준선 실측 후 조정 가능).
- **API:** Gemini 6조합 중 같은 규칙으로 1위. 하드 게이트 없음. 지연 p50/p95(네트워크 포함), 429 발생률, effective 지연 = max(실측, 60000/RPM), 색인 1회 비용(토큰 실측)을 기록한다.
- 정확도는 1회 측정(결정적). 지연만 3회 반복.

## 7. 산출물

- `data/eval/results/embedding-benchmark-YYYY-MM-DD/`
  - `corpus.jsonl.sha256`, `results.json`(조합 × 집계 단위 × 지표, bootstrap 구간, 지연·VRAM·비용)
  - `report.md` — 9조합 표, 로컬 1위·API 1위와 판정 근거, 한계(평가셋 편향·만료 공고 포함)
- gitignore: `data/eval/cache/`(코퍼스 jsonl, `.npy` — 모델당 최대 약 110MB)
- 개발 문서: `docs/STATUS.md` 갱신, `backend/docs/backend_ver_log.md` Minor 버전 기록

## 8. 테스트 (TDD)

- 순수 로직: 절단 후 단위 노름, 전수 검색 순위, `top1`·`ndcg_at_k` 경계(정답 없음·복수 정답), bootstrap 시드 재현성·동일 입력 시 구간 0 포함.
- 어댑터: `dim`/`model` 기본값이 현재 값과 같음(운영 회귀), bge-m3 어댑터 요청 바디(httpx MockTransport).
- 평가셋: `subset`/`hard_kind` 필드가 있어도 `evaluate_rag`·`review_evalset`이 기존대로 동작.
- 실제 모델·API 호출은 테스트하지 않는다(CLI 실행으로 확인).

## 9. 확인 사항 (구현 중 해소)

1. gemini-embedding-2가 `task_type`과 `output_dimensionality`를 001과 같이 받는지 — 공식 문서로 확인하고, 다르면 해당 어댑터만 분기한다(Strategy). → 해소(10/4): gemini-embedding-2는 task_type 미지원, 프롬프트 프리픽스로 대체(Task 2).
2. Ollama `bge-m3`의 실제 양자화 — `ollama show`로 확인해 보고서에 적는다. → F16(10/4 `ollama show bge-m3` 확인).
3. Gemini 2종 × 8.9k청크 색인 시 429 — 기존 재시도 정책을 그대로 쓰고 발생 횟수를 기록한다. → 재시도 0회(latency.json, 두 모델 모두).

## 10. 범위 밖

- 리랭커, BM25·하이브리드 검색, 추가 후보 모델(KURE, Qwen3-8B 등).
- 채택 모델의 운영 반영(스키마 변경·halfvec·재색인). 결과를 보고 별도 스펙으로 다룬다.
