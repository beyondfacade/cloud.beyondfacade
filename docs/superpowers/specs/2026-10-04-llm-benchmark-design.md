# LLM 모델 평가 — 리포트 작성·의도 관문 (2026-10-04)

> 목적: 한정된 자원(GPU 16GB 1장)에서 온프레미스로 돌릴 LLM을 가성비 기준으로 고르고, 온라인(Gemini)과 비교한다.
> 참고 실험: research.remakeday.com/experiments/model-selection (Core·NPC 역할별 평가, 하드 게이트, n=1 스모크 → n=3 본실험, 동시 상주).
> 선행: 임베딩 평가(`2026-10-04-embedding-benchmark-design.md`) — 같은 원칙(동률이면 작은 모델)으로 bge-m3@1024를 채택했다.

## 1. 현황

| 역할 | 현재 구성 | 호출 형태 |
|---|---|---|
| 창업 경고 리포트 작성 (agent BC) | `hybrid` — gemini-2.5-flash 주, 실패 시 gemma4:12b (`FallbackLLMAdapter`) | 사실 묶음(facts)을 먼저 수집해 첫 메시지에 넣고, LLM이 6개 절(판정·이유·유사 사례·조건·대안·지원사업)을 스트리밍한다. 도구는 facts에 없는 것(자금 계산·RAG 재검색)에만 |
| 의도 관문 폴백 (intent BC) | gemini-2.5-flash만 (로컬 없음) | 규칙이 못 푼 자유문에서 `region_name`(동 427개 중)·`industry_id`·`budget_krw`를 JSON 스키마로 1콜 추출, temperature 0 |

- 기존 `run_agent_eval`(9/21, 시나리오 10)은 리포트 v2 이전(5섹션·도구 중심 루프) 기준이라 그대로 못 쓴다.
- GPU: RTX 5060 Ti 16GB. 임베딩 bge-m3(Ollama 상주 664MB)와 같이 올라가야 한다.

## 2. 후보 모델

| 모델 | 크기(Q4_K_M) | 도구 | 리포트 | 관문 | 비고 |
|---|---|---|---|---|---|
| gemma4:12b | 7.6GB | O | O | O | 현행 로컬 폴백 — 우대 없음 |
| gemma4:e4b | 9.6GB | O | O | O | |
| kanana1.5:8b | 4.9GB | O | O | O | 한국어 특화 |
| qwen3.5:9b | 6.6GB | O | O | O | |
| qwen3.5:4b | 3.4GB | O | O | O | |
| qwen3.5:2b | 1.9GB | O | — | O | 관문 전용(가성비 확인) |
| exaone3.5:7.8b | 4.8GB | **X** | O(도구 없이) | — | Ollama 템플릿에 도구 처리 없음(`does not support tools`). **라이선스 EXAONE 1.1 NC(비상업)** — 채택 불가, 참고 비교군 |
| gemini-2.5-flash | API | O | O | O | 온라인 비교군, 게이트 없음 |

- 라이선스: Qwen3.5 Apache 2.0, Gemma 이용약관(상업 가능). kanana1.5는 Apache 2.0으로 알려져 있으나 구현 중 모델 카드로 확인한다(§9).

## 3. 평가셋

### 3-1. 의도 관문 — `data/eval/intent_evalset.jsonl` (약 80건)
한 줄: `{"id", "text", "kind", "expected": {"region_name", "industry_id", "budget_krw"}, "status"}`.

| `kind` | 내용 | 기대 |
|---|---|---|
| `landmark` | 지명·랜드마크("홍대 근처 카페") | 마스터의 동 이름으로(서교동) |
| `industry_slang` | 업종 구어체("커피집", "피시방", "미장원") | 업종 id |
| `budget` | 예산 표현("5천 정도", "1억 2천", "삼천만원") | 원 단위 정수 |
| `missing` | 일부 정보 없음 | 없는 필드는 null |
| `out_of_scope` | 서울 밖·미지원 업종 | null (지어내기 탐지) |
| `compound` | 여러 조건이 섞인 장문 | 세 필드 모두 |

- 라벨은 서브에이전트가 마스터 사전(동·구·업종)을 보고 작성 → 사용자 검수(`status` candidate → confirmed). 본지표는 confirmed만.
- 규칙 엔진을 거치지 않고 `IntentLlmPort.extract`를 직접 부른다. 모든 모델에 같은 지시문(동 427개 포함)과 같은 JSON 스키마.

### 3-2. 리포트 — `data/eval/report_scenarios.jsonl` (12건)
한 줄: `{"id", "region_code", "industry_id", "question", "tags"}`.
- 판정 4종(비추천·조건부·경고 없음·보류)을 고루, 데이터 일부 없음(편의점·어린이집 스냅샷 등), 응답 규칙 4종(차별 표현·재난기 폐업률 왜곡·금융 규제·신뢰 등급)이 걸리는 질문, 도구가 필요한 질문(자금 계산)을 포함한다.
- **facts 고정**: `freeze`가 12건의 facts를 한 번 수집해 `data/eval/report_facts/<id>.json`으로 저장하고, 모든 모델에 같은 facts를 넣는다(`ReportFactsCollector.collect`를 대체하는 고정 객체). 데이터 갱신과 무관하게 모델만 비교한다.
- 도구: EXAONE 외 모델은 현행 도구 목록 그대로, EXAONE은 빈 도구 목록(`tools: []` — 정상 동작 확인). 도구가 필요한 시나리오의 EXAONE 결과는 "도구 없음" 표시.

### 3-3. 반복
- 리포트: 모델당 12건 × 3회. 자동 채점은 전부, 서브에이전트 판정은 1회차만(7모델 × 12 = 84건, 모델명 가림).
- 관문: 80건 × 3회 (temperature 0이라 결과는 거의 같고, 반복은 지연 측정용). 정확도는 1회차, 지연은 3회 전부.
- 단계: 0 프로토콜 호환(각 모델 1건) → 1 스모크(n=1) → 2 본실험(n=3) → 3 동시 상주.

## 4. 지표·게이트

### 4-1. 리포트
| 구분 | 기준 |
|---|---|
| 게이트 1 완주율 | ≥ 0.95 — 오류 없이 6개 절 모두 생성 |
| 게이트 2 판정 일치 | = 1.00 — 리포트의 판정 단계가 facts의 verdict와 같다(§0-10 판정은 규칙) |
| 게이트 3 숫자 지어내기 | ≤ 0.05 — facts에 없는 숫자가 하나라도 나온 리포트 비율 |
| 게이트 4 응답 규칙 | 위반 0건 |
| 게이트 5 지연 | 첫 글자 p95 ≤ 5초, 완료 p95 ≤ 60초 (LLM 호출 시작 기준 — facts는 고정이라 수집 시간 제외) |
| 주 지표 | 서브에이전트 품질 점수 = 근거 충실도(1~5) + 자연스러움(1~5) |

숫자 지어내기 판정: 본문에서 숫자(쉼표·%·만/억 단위)를 뽑아 facts JSON의 모든 숫자와 대조. 비율↔퍼센트(0.123↔12.3%), 만원 단위, 표시 자릿수 반올림은 같은 값으로 본다. 불일치 숫자 목록을 결과에 남겨 사람이 오탐을 확인할 수 있게 한다.

### 4-2. 의도 관문
| 구분 | 기준 |
|---|---|
| 게이트 1 스키마 | 통과율 ≥ 0.98 |
| 게이트 2 지어내기 | ≤ 0.05 — `missing`·`out_of_scope`에서 null이어야 할 필드에 값을 만든 비율 |
| 게이트 3 지연 | p95 ≤ 3초 |
| 주 지표 | 지역·업종 동시 정답률. 예산 정확도는 보조 |

### 4-3. 판정 규칙 (두 역할 공통)
1. 게이트를 통과한 **로컬** 모델 중 주 지표 1위.
2. 1위와 문항별 점수의 paired bootstrap(n=10000, seed 0) 95% 구간이 0을 포함하면 동률.
3. 동률 중 **VRAM이 작은 순 → p95가 짧은 순**. 현행 gemma4:12b에 우대 없음.
4. 자원 조합 게이트: 선택한 리포트 모델 + 관문 모델 + bge-m3를 함께 올려 밀려나지 않아야 한다(`ollama ps` + nvidia-smi). 두 역할이 같은 모델이면 한 번만 올리는 조합으로 따로 표시.
5. 온라인 gemini-2.5-flash는 같은 지표로 비교만 하고 비용(토큰 × 가격, 확인일·URL)과 지연을 기록한다.

### 4-4. 통제
- 양자화 Q4_K_M(Ollama 기본 태그), thinking 끔(`think: false`, gemma4·qwen3.5), temperature 리포트 0.3·관문 0(현행과 같게), 입력(facts·문항·지시문) 고정.

## 5. 구성 요소

| 구성 | 위치 | 내용 |
|---|---|---|
| Ollama LLM 어댑터 옵션 | `apps/agent/adapter/outbound/llm/ollama_llm_adapter.py` | `think`, `temperature` 인자(기본값은 현 동작 그대로) |
| 로컬 관문 추출기 | `apps/intent/adapter/outbound/llm/ollama_intent_llm_adapter.py` (신규) | `IntentLlmPort` 구현. Gemini 어댑터와 같은 지시문·스키마, Ollama `format`에 JSON 스키마, temperature 0, 실패 시 None |
| 리포트 벤치 CLI | `apps/agent/adapter/inbound/cli/benchmark_report.py` | `freeze` / `run --model` / `score` / `judge export·import` / `residency` / `evaluate` |
| 관문 벤치 CLI | `apps/intent/adapter/inbound/cli/benchmark_intent.py` | `run --model` / `evaluate` |
| 공통 통계·판정 | `core/`로 승격 | 임베딩 하네스의 `paired_bootstrap_ci`·`percentile`·동률 판정을 옮기고 rag 하네스도 그것을 쓰게 바꾼다(BC 간 CLI import 방지) |
| 평가셋 생성·검수 | 관문 평가셋은 서브에이전트 라벨 → 사용자 검수 시트 | 임베딩 평가셋 흐름(파일 export/import)과 같은 방식 |

운영 경로는 바꾸지 않는다(리포트 hybrid, 관문 Gemini). 채택·교체는 결과를 보고 별도로 결정한다.

## 6. 산출물
- `data/eval/results/llm-benchmark-YYYY-MM-DD/` — `results.json`(모델 × 문항 원자료, 게이트, bootstrap 구간, VRAM·지연·비용), `report.md`(역할별 표, 게이트 통과, 동률 판정, 추천 조합, 온라인 비교, 한계).
- 개발 문서: `docs/STATUS.md`, `backend/docs/backend_ver_log.md`.

## 7. 테스트 (TDD)
- 순수 로직: 숫자 추출·정규화·대조(비율/퍼센트, 만·억, 반올림), 판정 일치 판별, 6절 완성 판별, 관문 채점(정답·null·지어내기), 공통 통계 이동 후 rag 하네스 회귀.
- 어댑터: Ollama LLM 어댑터 `think`·`temperature`가 요청 바디에 실리고 기본값은 기존과 같음, Ollama 관문 추출기 요청 바디·실패 시 None(MockTransport).
- 고정 facts 객체가 `AnalysisInteractor`에 그대로 들어가 동작함(가짜 LLM).
- 실제 모델·API 호출은 테스트하지 않는다(CLI 실행으로 확인).

## 8. 범위 밖
- 운영 모델 교체(결과 후 별도 결정), 모델 파인튜닝, 32B급 이상 모델, 동시 다중 사용자 부하(전체 과부하 테스트에서 별도).

## 9. 확인 사항 (구현 중 해소)
1. kanana1.5:8b 라이선스 — 모델 카드로 확인해 보고서에 적는다.
2. gemma4·qwen3.5에서 `think: false`가 실제로 thinking을 끄는지 — 응답에 thinking 필드가 비는지 확인.
3. Ollama `format`(JSON 스키마)이 각 후보에서 동작하는지 — 0단계 프로토콜 호환에서 확인, 안 되면 해당 모델은 관문 게이트 1로 판정.
4. gemini-2.5-flash 가격 — 공식 가격표(확인일·URL)로.

### 해소 결과 (2026-10-05)
1. kanana1.5 라이선스 — Hugging Face 모델 카드(kakaocorp/kanana-1.5-8b-instruct-2505)에 apache-2.0로 표기. `ollama show --license`는 출력이 없어 모델 카드만 확인.
2. `think: false` — 동작함. 어떤 모델의 어떤 절에도 thinking 텍스트가 없었다.
3. Ollama `format` — Gemini `nullable`은 무시된다(문자열 "null" 관측). type 합집합(["string","null"])을 써야 한다.
4. gemini-2.5-flash 가격 — 입력 $0.30 / 출력 $2.50 per 1M 토큰(Standard, 확인일 2026-10-05, https://ai.google.dev/gemini-api/docs/pricing).
