# 에이전트 두뇌 비교 평가 (gemma3 vs Gemini)

> 실행일: 2026-09-21~22 · 시나리오 10 · 자동 채점 + 수동 검토 병기
> 원본: `data/eval/results/agent_gemma3_20260921T085001Z.jsonl`, `agent_gemini_20260922T022529Z.jsonl`

## 요약

| 지표 | gemma3(로컬=gemma4:12b) | gemini-2.5-flash |
|---|---:|---:|
| 도구 성공률(스킵 제외) | 100% | 100% |
| 평균 도구 호출 수 | 3.4 | 5.0 |
| 리포트 5섹션 완성률 | 50% | 90% |
| 평균 소요 | 39.9s | 17.4s |
| 평균 토큰(입+출) | 10997 | 7570 |
| 자동 규칙 위반 감지 케이스 | 0/10 | 0/10 |

## 케이스별

| case | gemma3 섹션 | gemma3 ms | gemini 섹션 | gemini ms | gemma3 rules | gemini rules |
|---|---:|---:|---:|---:|---|---|
| 01_yeoksam_cafe | 2/5 | 28824 | 5/5 | 27360 | — | — |
| 02_jamwon_gym | 0/5 | 17738 | 5/5 | 18848 | — | — |
| 03_samsung_karaoke | 5/5 | 34659 | 5/5 | 22725 | — | — |
| 04_gasan_pcbang | 5/5 | 38385 | 5/5 | 16524 | — | — |
| 05_cheongun_salon | 0/5 | 66324 | 5/5 | 17084 | — | — |
| 06_cheongdam_billiard | 1/5 | 57401 | 0/5 | 6050 | — | — |
| 07_convenience_partial | 0/5 | 26855 | 5/5 | 13674 | — | — |
| 08_childcare_partial | 5/5 | 30339 | 5/5 | 15012 | — | — |
| 09_daelim_cafe_foreigner | 2/5 | 47068 | 5/5 | 23255 | — | — |
| 10_yeoksam_realestate_loan | 5/5 | 51196 | 5/5 | 13449 | — | — |

## 자동 채점 한계

- `rule_hits`는 은행명+추천 큐·외국인 비하 키워드 근사만 본다(부정문·맥락 미판별).
- 최종 규칙 위반(차별 표현 0, 특정 은행 추천 금지)은 jsonl의 `report_md`를 **수동 검토**해야 한다.
- 섹션 완성률: `"분석 데이터가 부족합니다"`만 있으면 incomplete로 친다.

## 모델 배선 메모

- 로컬 API 키 `gemma3` → Ollama **gemma4:12b** (gemma3:12b는 tools capability 없음)
- Gemini 기본 → **gemini-2.5-flash** (gemini-2.0-flash 폐기; gemini-3.6-flash는 thought_signature 요구로 현 어댑터 보류)

## 두뇌 권고안 (결정권: 사용자)

| 옵션 | 근거 |
|---|---|
| **A. Gemini 단독** | 섹션 완성률·지연이 유리(약 87% vs 50%, ~17s vs ~40s). 외부 키·쿼터 의존. |
| **B. 로컬(gemma4) 단독** | 오프라인·비용 0. 섹션 완성률이 낮아 프롬프트/도구 사용 튜닝 필요. |
| **C. 혼합** | 데모·품질은 Gemini, 야간 배치·폴백은 로컬. Composition Root 레지스트리로 이미 가능. |

권고는 수치 기반 제안일 뿐이며, **최종 채택은 사용자 결정**이다.
