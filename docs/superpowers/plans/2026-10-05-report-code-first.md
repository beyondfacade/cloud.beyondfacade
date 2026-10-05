# 리포트 코드 우선 구조 (사실은 코드, 해석은 LLM 한 단락) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 리포트 6개 절을 코드가 facts로 결정적으로 쓰고, LLM은 맨 위 해석(`answer`) 한 단락(숫자 없음)만 쓰게 바꾼다 — 도구 루프 제거, 새 숫자 가드, SSE·저장·벤치·화면까지.

**Architecture:** 순수 도메인 모듈 `report_sections.py`가 facts → 6개 절 마크다운(dict 디스패치)을 쓰고, 인터랙터는 사실 수집 직후 그 6개 절을 `report_delta`로 바로 내보낸 뒤 LLM 해석을 비스트리밍 `chat()`으로 끝까지 받아 `guard_answer`(링크 제거 → 판정 모순 검사 → 숫자 문장 삭제)를 거쳐 한 번에 내보낸다. 가드 실패·호출 실패는 다음 모델(운영 hybrid: 로컬 gemma4:12b)로, 그래도 안 되면 코드 한 줄로 맺는다. 벤치는 해석 단락만 채점하고, 코드 절은 모델 호출 없는 `sections-check`로 150건을 자동 검사한다.

**Tech Stack:** Python 3.14 · FastAPI(SSE) · pytest / Next.js App Router · React · TypeScript · Vitest (프론트는 Codex `codex exec` 위임)

**Spec:** `docs/superpowers/specs/2026-10-05-report-code-first-design.md` (구속력 있는 원천 — 실행자는 이 계획과 함께 읽는다)

## Global Constraints

- 작업 위치: 워크트리 `/home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first` (브랜치 `feat/report-code-first`). 모든 경로는 이 워크트리 기준이다.
- 백엔드 테스트 명령(워크트리에는 `.venv`가 없다 — 메인 저장소의 것을 쓴다): `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/ -q` (기준선 1301 passed).
- 샘플링: 온도 0·seed 42 단일 원천 `apps/agent/domain/services/report_sampling.py`(`REPORT_TEMPERATURE = 0.0`, `REPORT_SEED = 42`) — 바꾸지 않는다.
- LLM 범위: 맨 위 `answer` 한 단락(3~5문장)만. 6개 섹션은 전부 코드. 질문이 없으면 총평 한 단락("이 동네에서 이 업종을 한다면 먼저 볼 것") — 화면 구성은 질문 유무와 무관하게 같다.
- `answer` 출력 규칙: 질문에 직접 답한다. **숫자·링크·공고 번호를 쓰지 않는다.** 판정 등급을 바꾸지 않는다. 규칙 ①(차별 금지)·②(재난기 왜곡)·③(대출 중개·상품 추천 금지) 유지. 자료 부족 섹션을 추정으로 메우지 않는다("자료가 부족해 판단할 수 없다").
- `answer` 가드: 숫자가 든 문장은 지운다(문장 단위 — 한글 문장 끝 기준), 링크·공고 번호 제거(기존 `UrlStripper`), 판정과 모순되는 명시적 등급 단정이면 단락 전체 실패 → 다음 모델(기존 `verdict_contradiction`). `answer`는 끝까지 모았다가 검사 후 한 번에 내보낸다.
- 폴백: Gemini → gemma4:12b(`num_ctx` 그대로 32768) → 둘 다 실패하거나 가드 후 빈 단락이면 코드 한 줄 — 정확히 `질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요.`
- 섹션 제목(정확히): `verdict` 판정 · `reasons` 왜 안 되나 · `analogs` 유사 사례 · `conditions` 그래도 한다면 · `alternatives` 대안 동네·업종 · `funding` 대안 업종 지원사업.
- 섹션 순서: 화면·저장 `answer → verdict → reasons → analogs → conditions → alternatives → funding`. SSE 방출 순서: `agent_status`·`facts`(지금과 같다) → 코드 6개 절을 `report_delta {section, markdown}`로 즉시(절당 한 조각) → `report_delta {section: "answer"}` → `report_done`(인용은 사실 묶음에서 코드가 만든 것만, 도구 인용 제거).
- 코드 섹션 원칙: ① 모든 숫자에 범위(무엇의·어디의·언제의) ② 자료가 없으면 "자료 부족 — 이유", 빈칸을 추정으로 채우지 않음 ③ 신뢰 태그는 코드가 붙임 — 정형 값 `[확인된 사실]`, 뉴스·검색 `[참고 신호]`, `LeadingTagGuard`는 코드 섹션에 쓰지 않음 ④ 시간대 문장은 프론트 `hour-gap-sentence.ts`와 같은 규칙.
- 저장: 저장 리포트에 `answer` 섹션이 추가된다. 옛 저장 리포트(answer 없음)도 그대로 열려야 한다.
- 도구 호출·`_FINAL_REQUEST`·도구 인자 검사·도구 인용은 리포트 경로에서 제거. `agent_tools.py`의 리포트 전용 정의는 정리하되 `hit_to_dict`는 남긴다.
- CLAUDE.md §2: 과도한 테스트·선제적 복잡도 금지 — 섹션 문장 함수는 대표 사례(정상·자료 부족·참고 신호)만, 가드는 새 숫자 가드만. 도메인 모듈은 프레임워크 import 금지, 분기는 dict 디스패치, 주석은 한국어.
- 버전: backend **v0.68.0** — `backend/docs/backend_ver_log.md` 맨 위에 한 항목을 Task 1에서 열고 Task 2~5·7이 같은 항목에 줄을 보탠다. frontend **v0.53.0**(현재 최신 v0.52.1) — Codex 작업분.
- Task 1~6은 모델을 부르지 않는다. Task 7만 모델 호출(컨트롤러가 직접 실행).
- 커밋: 메시지 끝에 빈 줄 + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. push·amend는 하지 않는다(사용자가 직접).

## File Structure

| 파일 | 상태 | 책임 |
|---|---|---|
| `backend/apps/agent/domain/services/report_sections.py` | 생성 (Task 1) | facts → 6개 절 마크다운, 시간대 문장 포팅. 순수 모듈 |
| `backend/tests/test_report_sections.py` | 생성 (Task 1) | 절별 대표 사례 |
| `backend/apps/agent/domain/services/report_guards.py` | 수정 (Task 2 추가, Task 5 정리) | `drop_digit_sentences`·`GuardedAnswer`·`guard_answer` 추가, 스트리밍 절 가드 제거 |
| `backend/apps/agent/app/use_cases/analysis_interactor.py` | 전면 교체 (Task 3) | 사실 → 코드 절 → 해석 → 완료. 도구 루프 제거 |
| `backend/apps/agent/dependencies/analysis_dependencies.py` | 수정 (Task 3) | `retry_llm`(hybrid만 로컬) 배선, 도구 배선 제거 |
| `backend/apps/agent/domain/services/section_stream.py` | 수정 (Task 3), 축소 (Task 5) | `SECTION_ORDER`에 `answer` 맨 앞, `SectionSplitter` 제거 |
| `backend/apps/agent/domain/entities/agent_event_entity.py` | 수정 (Task 3) | report_delta 섹션 어휘 docstring |
| `backend/tests/test_agent_loop.py` | 전면 교체 (Task 3) | 새 SSE 계약 |
| `backend/tests/test_agent_router.py`, `backend/tests/test_agent_section_stream.py` | 수정 (Task 3, 5) | 저장 순서·순서 상수 |
| `backend/apps/agent/adapter/inbound/cli/benchmark_report.py` | 수정 (Task 4) | 해석 채점·`sections-check`·해석 판정 묶음 |
| `backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py` | 수정 (Task 4) | `unscoped_number_lines`·`missing_data_gaps`·`answer_packets` |
| `data/eval/report_answer_rubric.md` | 생성 (Task 4) | 해석 단락 판정 기준(Claude 150건·사람 20건 공용) |
| `backend/apps/agent/app/use_cases/agent_tools.py` | 축소 (Task 5) | `hit_to_dict`만 |
| `backend/apps/agent/domain/services/report_fallback.py`, `backend/tests/test_agent_report_fallback.py`, `backend/tests/test_agent_tools.py`, `backend/apps/agent/adapter/outbound/gateways/finance_facts_gateway.py` | 삭제 (Task 5) | 새 구조에서 쓰지 않음 |
| `frontend/src/shared/api/types.ts`, `frontend/src/features/agent-report/components/{report-view,report-visuals}.tsx`, `frontend/src/app/api/mock/fixtures.ts` + 테스트 | 수정 (Task 6, Codex) | `answer` 섹션 계약·"해석" 블록 |
| `data/eval/results/report-code-first-2026-10-05/` | 생성 (Task 7) | 150건 재평가 결과·notes |

---

### Task 1: 코드 섹션 문장 모듈 `report_sections.py`

**Files:**
- Create: `backend/apps/agent/domain/services/report_sections.py`
- Create: `backend/tests/test_report_sections.py`
- Modify: `backend/docs/backend_ver_log.md` (맨 위에 v0.68.0 항목 열기)

**Interfaces:**
- Consumes: `apps.agent.domain.services.report_guards.FUNDING_DISCLAIMER` (기존 상수 `"[확인된 사실] 금리·한도는 예상치이며, 신청 자격·한도는 공고 원문에서 확인해야 합니다."`)
- Produces:
  - `SECTION_TITLES: dict[str, str]` — 6개 절 이름 → 제목, 방출 순서
  - `build_sections(facts: dict) -> dict[str, str]` — `SECTION_TITLES` 순서, 값은 `"### {제목}\n\n{본문}"`
  - `hour_gap_sentence(bands: list[dict]) -> str | None` — 프론트 `hourGapSentence`와 같은 규칙
  - `HOUR_BAND_LABELS: dict[str, str]`, `FACT = "[확인된 사실]"`, `SIGNAL = "[참고 신호]"`, `missing(reason) -> str`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_report_sections.py` (테스트 facts는 커밋된 평가셋 `data/eval/report_facts_150/e001.json`(송정동 한식)을 바탕에 두고 다룰 키만 바꿔 끼운다):

```python
"""report_sections — 리포트 6개 절을 facts만으로 쓰는 순수 모듈 (LLM·DB 없음)."""

import json
from pathlib import Path

from apps.agent.domain.services.report_guards import FUNDING_DISCLAIMER
from apps.agent.domain.services.report_sections import (
    SECTION_TITLES,
    build_sections,
    hour_gap_sentence,
)

# 평가셋 고정 facts(송정동 한식) — 테스트마다 다룰 키만 바꿔 끼운다
_BASE = json.loads(
    (Path(__file__).resolve().parents[2] / "data/eval/report_facts_150/e001.json").read_text(encoding="utf-8")
)
_UNAVAILABLE = {"available": False, "reason": "판정 대상 업종이 아니다 — 이 업종은 판정을 내리지 않는다"}


def _signal(key: str, level: str, evidence: str, advisory: bool = False) -> dict:
    return {"key": key, "level": level, "evidence": evidence, "advisory": advisory}


_RED = {
    "available": True,
    "verdict_code": "red",
    "on_count": 2,
    "strong_count": 2,
    "computed_at": "2026-10-04T19:34:24+00:00",
    "signals": [
        _signal("net_outflow", "strong", "지난 12개월 폐업 16곳, 개업 8곳 (순유출률 +20%, 서울 한식 상위 1%)"),
        _signal("survival_cliff", "unavailable", "표본 부족 — 3년 전 개업 코호트 1곳 (10곳 미만)"),
        _signal("saturation", "off", "상주인구 1,000명당 한식 3.4곳 (서울 상위 61%)"),
        _signal("shrinking", "strong", "서울시 상권변화지표 '상권축소' (2026년 2분기, 동 전체 기준)", advisory=True),
    ],
}


def _body(section: str, **facts) -> str:
    """제목 줄을 뗀 절 본문."""
    return build_sections({**_BASE, **facts})[section].split("\n\n", 1)[1]


def _band(hour_band: str, footfall: float, sales: float) -> dict:
    return {"hour_band": hour_band, "footfall_intensity": footfall, "sales_intensity": sales, "gap": sales - footfall}


def test_여섯_절을_계약_순서로_제목과_함께_쓴다():
    sections = build_sections(_BASE)

    assert list(sections) == ["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"]
    assert all(sections[name].startswith(f"### {title}\n\n") for name, title in SECTION_TITLES.items())


def test_판정은_등급_라벨과_켜진_신호_수와_자료_부족_신호_수를_쓴다():
    assert _body("verdict", verdict=_RED) == (
        "[확인된 사실] 송정동 한식 판정: **비추천** — 경고 신호 3개 중 2개 켜짐(강한 신호 2개), "
        "1개는 자료 부족으로 계산하지 못함. 산출 2026-10-04."
    )


def test_판정을_내리지_않는_업종은_자료_부족과_이유를_쓴다():
    assert _body("verdict", verdict=_UNAVAILABLE) == (
        "[확인된 사실] 송정동 한식 판정: 자료 부족 — 판정 대상 업종이 아니다 — 이 업종은 판정을 내리지 않는다"
    )


def test_왜_안_되나는_켜진_신호_참고_신호_표본_부족을_쓰고_꺼진_신호는_뺀다():
    history = [
        {"year": 2019, "store_count": 41, "closure_rate": 0.0278},
        {"year": 2021, "store_count": 42, "closure_rate": 0.0976},
        {"year": 2026, "store_count": 33, "closure_rate": None},
        {"year": 2025, "store_count": 42, "closure_rate": 0.1905},
    ]
    shocks = [{"name": "최저임금 인상 — 2019년 시급 8,350원(+10.9%)", "start_date": "2019-01-01", "industry_specific": False}]

    assert _body("reasons", verdict=_RED, metrics_history=history, shocks=shocks) == (
        "- [확인된 사실] 순유출(송정동 한식): 지난 12개월 폐업 16곳, 개업 8곳 (순유출률 +20%, 서울 한식 상위 1%)\n"
        "- [확인된 사실] 생존 절벽(송정동 한식): 표본 부족 — 3년 전 개업 코호트 1곳 (10곳 미만)\n"
        "- [확인된 사실] 참고 — 상권 축소: 서울시 상권변화지표 '상권축소' (2026년 2분기, 동 전체 기준)\n\n"
        "[확인된 사실] 송정동 한식 연간 폐업률: 2019년 2.8% → 2025년 19.1%(점포 41곳 → 42곳). "
        "2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 늦춰져 왜곡됐을 수 있습니다.\n\n"
        "[확인된 사실] 외부 충격(한식 전용 기록은 없어 전 업종 공통 충격): 최저임금 인상(2019년)."
    )


def test_연도별_폐업률이_없으면_자료_부족이라고_쓴다():
    body = _body("reasons", verdict=_RED, metrics_history={"available": False, "reason": "조회 실패"}, shocks=[])

    assert "[확인된 사실] 송정동 한식 연간 폐업률: 자료 부족 — 조회 실패" in body
    assert "[확인된 사실] 외부 충격(한식): 자료 부족 — 기록 없음" in body


def test_유사_사례는_질문_속_유형부터_고정_문장을_옮기고_소식이_있을_때만_참고_신호를_붙인다():
    analogs = {
        "categories": [
            {"category": "minimum_wage", "reason": "current"},
            {"category": "pandemic", "reason": "question"},
        ],
        "current_events": [{"category": "minimum_wage", "summary_sentence": "최저임금 문장.", "overlap_sentence": None}],
        "analogs": [
            {"category": "pandemic", "summary_sentence": "코로나 문장.", "overlap_sentence": "겹친 정책 문장."},
            {"category": "pandemic", "summary_sentence": None, "overlap_sentence": None},  # 대표가 아닌 사례
        ],
        "outlooks": [{"category": "pandemic", "condition_sentence": None, "recommended_sentence": "강세 업종 문장."}],
        "recent_news": [
            {"category": "pandemic", "article_count": 2, "sentence": "최근 30일 영업제한 관련 뉴스는 2건입니다."},
            {"category": "minimum_wage", "article_count": 0, "sentence": "최근 30일 같은 조치 소식은 없습니다."},
        ],
    }

    assert _body("analogs", analogs=analogs) == (
        "[확인된 사실] 코로나 문장. 겹친 정책 문장. 강세 업종 문장. "
        "[참고 신호] 최근 30일 영업제한 관련 뉴스는 2건입니다.\n\n"
        "[확인된 사실] 최저임금 문장."
    )


def test_시간대_문장은_프론트와_같은_입력에_같은_문장을_낸다():
    # frontend/src/features/agent-report/lib/hour-gap-sentence.test.ts 와 같은 세 입력·같은 기대 문장
    cafe = [_band("00_06", 0.3, 0.05), _band("06_11", 1.0, 0.7), _band("11_14", 1.39, 2.99),
            _band("14_17", 1.4, 1.6), _band("17_21", 1.1, 1.2), _band("21_24", 0.5, 0.35)]
    assert hour_gap_sentence(cafe) == "사람은 오후(14~17시)에 가장 많고, 돈은 점심(11~14시)에 돕니다."
    assert hour_gap_sentence([_band("06_11", 0.8, 0.6), _band("17_21", 1.6, 1.9)]) == "사람과 돈이 저녁(17~21시)에 같이 몰립니다."
    assert hour_gap_sentence([_band("06_11", 1.5, 1.2), _band("11_14", 1.6, 1.1)]) == (
        "사람은 점심(11~14시)에 가장 많고, 돈은 아침(06~11시)에 돕니다."
    )


def test_그래도_한다면은_시간대_부족_이유와_상권_전체_기준값의_범위를_쓴다():
    change = {"available": True, "year_quarter": "20262", "change_name": "정체", "operating_months": 124.0,
              "closed_months": 54.0, "seoul": {"operating_months": 118.0, "closed_months": 54.0}}
    profile = {"year_quarter": "20262", "type_name": "주거형", "type_reason": "직장인구가 상주인구보다 적습니다.",
               "time_label_name": "밤(21~06시)", "peak_block_name": "밤(21~06시)", "trough_block_name": "저녁(17~21시)"}

    body = _body("conditions", hour_gap={"available": False, "reason": "시간대 어긋남 자료가 없다"},
                 profile=profile, commerce_change=change, budget=None)

    assert body == (
        "[확인된 사실] 시간대(송정동 한식): 자료 부족 — 시간대 어긋남 자료가 없다\n\n"
        "[확인된 사실] 동네 유형(송정동, 2026년 2분기): 주거형 — 직장인구가 상주인구보다 적습니다. "
        "사람 흐름: 밤(21~06시) — 가장 많은 때 밤(21~06시), 가장 적은 때 저녁(17~21시).\n\n"
        "[확인된 사실] 상권 영업 기간(송정동 상권 전체·업종 무관, 2026년 2분기): 영업 중 점포 평균 124개월, "
        "폐업 점포 평균 54개월 — 서울 동 상권 전체 기준값은 118개월·54개월입니다. 상권변화지표: 정체."
    )


def test_예산이_있으면_자금_계획_화면_안내를_한_줄_덧붙인다():
    body = _body("conditions", hour_gap={"available": False, "reason": "없음"}, profile={"available": False, "reason": "없음"},
                 commerce_change={"available": False, "reason": "없음"}, budget=50_000_000)

    assert body.endswith("[확인된 사실] 입력한 예산으로 총 준비자금·조달 필요액·손익분기 매출을 계산하려면 자금 계획 화면을 이용하세요.")


def test_대안은_두_축을_각_최대_3개까지_등급_라벨_그대로_쓴다():
    alternatives = {
        "available": True,
        "industries": [{"industry_name": "카페", "verdict_code": "clear"}, {"industry_name": "미용실", "verdict_code": "orange"}],
        "regions": [{"region_name": n, "verdict_code": "clear"} for n in ("부암동", "평창동", "교남동", "청운효자동")],
    }

    assert _body("alternatives", alternatives=alternatives) == (
        "[확인된 사실] 같은 동네(송정동)의 다른 업종\n- 카페 (경고 없음)\n- 미용실 (조건부)\n\n"
        "[확인된 사실] 같은 업종(한식)의 다른 동네\n- 부암동 (경고 없음)\n- 평창동 (경고 없음)\n- 교남동 (경고 없음)"
    )
    assert _body("alternatives", alternatives=_UNAVAILABLE).startswith("[확인된 사실] 대안(송정동 한식): 자료 부족 — ")


def test_지원사업은_공고_제목_원문과_해당_가능성과_예상치_고지를_쓴다():
    candidates = [
        {"title": "[서울] 2026년 새 길 여는 폐업지원 사업 모집 공고", "org": "서울특별시", "deadline": None,
         "apply_period": "예산 소진시까지", "url": "https://www.bizinfo.go.kr/x?pblancId=PBLN_1"},
        {"title": "창업기업 모집 공고", "org": "중소벤처기업부", "deadline": "2026-10-06", "apply_period": "2026-09-01 ~ 2026-10-06"},
    ]

    body = _body("funding", funding_candidates=candidates)

    assert body == (
        "[확인된 사실] 송정동 한식 조건으로 찾은 공고 후보입니다 — 자격 확정이 아니라 해당 가능성이며, "
        "지원 대상은 공고 원문에서 확인해야 합니다.\n\n"
        "- 「[서울] 2026년 새 길 여는 폐업지원 사업 모집 공고」 — 서울특별시, 접수 예산 소진시까지\n"
        "- 「창업기업 모집 공고」 — 중소벤처기업부, 마감 2026-10-06\n\n"
        f"{FUNDING_DISCLAIMER}"
    )
    assert "http" not in body and "PBLN_" not in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_report_sections.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.agent.domain.services.report_sections'`

- [ ] **Step 3: Write minimal implementation**

`backend/apps/agent/domain/services/report_sections.py`:

```python
"""리포트 6개 절을 facts만으로 쓰는 순수 모듈 (stdlib만 import).

설계서 docs/superpowers/specs/2026-10-05-report-code-first-design.md §4 — 결론과 수치는 코드가 사실에서 쓰고,
LLM은 맨 위 해석(answer) 한 단락만 쓴다. 원칙:
① 숫자에는 범위(무엇의·어디의·언제의)를 붙인다 — 줄마다 동·업종 이름이나 "서울"을 적는다.
② 자료가 없으면 "자료 부족 — 이유"를 쓰고 추정으로 메우지 않는다.
③ 신뢰 태그는 코드가 붙인다 — 정형 값 [확인된 사실], 뉴스 [참고 신호].
④ 화면 차트와 같은 규칙을 쓴다 — 시간대 문장은 프론트 `hour-gap-sentence.ts`와 같은 규칙.
"""

from apps.agent.domain.services.report_guards import FUNDING_DISCLAIMER

FACT = "[확인된 사실]"
SIGNAL = "[참고 신호]"

# 절 이름 → 제목. 방출·저장 순서다(section_stream.SECTION_ORDER는 answer 다음에 이 순서).
SECTION_TITLES = {
    "verdict": "판정",
    "reasons": "왜 안 되나",
    "analogs": "유사 사례",
    "conditions": "그래도 한다면",
    "alternatives": "대안 동네·업종",
    "funding": "대안 업종 지원사업",
}

# 판정 코드 → 라벨. 프론트 `shared/verdict.ts` LABELS와 같은 어휘다.
_VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}
# 신호 키 → 이름. 프론트 `shared/verdict.ts` SIGNAL_LABELS와 같은 어휘다.
_SIGNAL_LABELS = {
    "net_outflow": "순유출",
    "survival_cliff": "생존 절벽",
    "early_closure": "조기 폐업",
    "saturation": "포화",
    "shrinking": "상권 축소",
    "closure_rate": "폐업률",
    "tobacco_gap": "담배권 빈자리",
    "trade_per_office": "사무소당 거래",
}
# 시간대 6구간 표기. 프론트 `neighborhood-charts.ts` HOUR_BAND_LABELS와 같다.
HOUR_BAND_LABELS = {
    "00_06": "새벽(00~06시)",
    "06_11": "아침(06~11시)",
    "11_14": "점심(11~14시)",
    "14_17": "오후(14~17시)",
    "17_21": "저녁(17~21시)",
    "21_24": "밤(21~24시)",
}
_MAX_PER_AXIS = 3  # 대안 두 축 각 최대 3개
_DISASTER_YEARS = range(2020, 2023)
_DISASTER_NOTE = "2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 늦춰져 왜곡됐을 수 있습니다."
_BUDGET_LINE = f"{FACT} 입력한 예산으로 총 준비자금·조달 필요액·손익분기 매출을 계산하려면 자금 계획 화면을 이용하세요."
# 충격 목록이 이 업종 것인지(True) 전 업종 공통으로 되돌린 것인지(False) — report_facts._shocks가 정한다
_SHOCK_SCOPES = {True: "{industry}에 영향을 준 충격", False: "{industry} 전용 기록은 없어 전 업종 공통 충격"}


def missing(reason: str | None) -> str:
    return f"자료 부족 — {reason or '이유 미상'}"


def _missing_reason(value: object) -> str | None:
    """수집 실패·판정 불가 자리(`{"available": False, "reason": ...}`)면 그 이유, 아니면 None.

    목록 자리(지표 이력·충격·공고)도 실패하면 이 dict가 온다 — 모양을 보고 가른다.
    """
    if isinstance(value, dict) and value.get("available") is False:
        return value.get("reason") or "이유 미상"
    return None


def _names(facts: dict) -> tuple[str, str]:
    region = facts.get("region") or {}
    return region.get("name") or "이 동", region.get("industry_name") or "이 업종"


def _quarter(year_quarter: str | None) -> str:
    """'20262' → '2026년 2분기'."""
    return f"{year_quarter[:4]}년 {year_quarter[4:]}분기" if year_quarter else "최신 분기"


# ── 판정 ─────────────────────────────────────────────────────


def _verdict(facts: dict) -> str:
    region, industry = _names(facts)
    verdict = facts.get("verdict") or {}
    if not verdict.get("available"):
        return f"{FACT} {region} {industry} 판정: {missing(verdict.get('reason'))}"
    judged = [s for s in verdict.get("signals") or [] if not s.get("advisory")]
    short = sum(s.get("level") == "unavailable" for s in judged)
    label = _VERDICT_LABELS.get(verdict.get("verdict_code"), verdict.get("verdict_code"))
    tail = f", {short}개는 자료 부족으로 계산하지 못함" if short else ""
    return (
        f"{FACT} {region} {industry} 판정: **{label}** — 경고 신호 {len(judged)}개 중 "
        f"{verdict.get('on_count', 0)}개 켜짐(강한 신호 {verdict.get('strong_count', 0)}개){tail}. "
        f"산출 {str(verdict.get('computed_at') or '')[:10]}."
    )


# ── 왜 안 되나 ───────────────────────────────────────────────

# 참고 신호(advisory) 여부 → 줄 모양 (if/elif 대신 테이블 디스패치). 꺼진 신호는 쓰지 않는다.
# 켜진 신호와 표본 부족 신호는 같은 모양이다 — 표본 부족은 evidence가 "표본 부족 — …"으로 이유를 말한다.
_SIGNAL_LINES = {
    False: lambda name, evidence, where: f"- {FACT} {name}({where}): {evidence}",
    True: lambda name, evidence, where: f"- {FACT} 참고 — {name}: {evidence}",
}


def _signals(verdict: dict, region: str, industry: str) -> str:
    if not verdict.get("available"):
        return f"{FACT} 경고 신호({region} {industry}): {missing(verdict.get('reason'))}"
    where = f"{region} {industry}"
    lines = [
        _SIGNAL_LINES[bool(s.get("advisory"))](_SIGNAL_LABELS.get(s.get("key"), s.get("key")), s.get("evidence"), where)
        for s in verdict.get("signals") or []
        if s.get("level") != "off"
    ]
    return "\n".join(lines) or f"{FACT} {where}: 켜진 경고 신호 없음."


def _closure_trend(history: object, region: str, industry: str) -> str:
    reason = _missing_reason(history)
    rows = [r for r in history or [] if r.get("closure_rate") is not None] if reason is None else []
    if not rows:
        return f"{FACT} {region} {industry} 연간 폐업률: {missing(reason or '연도별 폐업률 없음')}"
    first, last = rows[0], rows[-1]
    line = (
        f"{FACT} {region} {industry} 연간 폐업률: {first['year']}년 {first['closure_rate'] * 100:.1f}% → "
        f"{last['year']}년 {last['closure_rate'] * 100:.1f}%(점포 {first['store_count']}곳 → {last['store_count']}곳)."
    )
    return line + (f" {_DISASTER_NOTE}" if any(r["year"] in _DISASTER_YEARS for r in rows) else "")


def _shocks(shocks: object, industry: str) -> str:
    reason = _missing_reason(shocks)
    if reason is not None or not shocks:
        return f"{FACT} 외부 충격({industry}): {missing(reason or '기록 없음')}"
    scope = _SHOCK_SCOPES[bool(shocks[0].get("industry_specific"))].format(industry=industry)
    names = ", ".join(f"{s['name'].split(' — ')[0]}({str(s.get('start_date'))[:4]}년)" for s in shocks)
    return f"{FACT} 외부 충격({scope}): {names}."


def _reasons(facts: dict) -> str:
    region, industry = _names(facts)
    return "\n\n".join(
        [
            _signals(facts.get("verdict") or {}, region, industry),
            _closure_trend(facts.get("metrics_history"), region, industry),
            _shocks(facts.get("shocks"), industry),
        ]
    )


# ── 유사 사례 ────────────────────────────────────────────────


def _category_paragraph(analogs: dict, category: str) -> str:
    """한 유형 = 한 문단 — 사례·종합 고정 문장([확인된 사실]) 뒤에 그 유형의 최근 조치 소식([참고 신호]).

    소식이 없으면(기사 0건·확인 못 함) 줄을 생략한다 — "없다"고 쓰지 않는다(설계서 §4).
    """
    events = [*(analogs.get("current_events") or []), *(analogs.get("analogs") or [])]
    outlook = next((o for o in analogs.get("outlooks") or [] if o.get("category") == category), {})
    sentences = [
        *(s for e in events if e.get("category") == category for s in (e.get("summary_sentence"), e.get("overlap_sentence")) if s),
        *(s for s in (outlook.get("condition_sentence"), outlook.get("recommended_sentence")) if s),
    ]
    news = [r["sentence"] for r in analogs.get("recent_news") or [] if r.get("category") == category and r.get("article_count")]
    parts = [*([f"{FACT} " + " ".join(sentences)] if sentences else []), *([f"{SIGNAL} " + " ".join(news)] if news else [])]
    return " ".join(parts)


def _analogs(facts: dict) -> str:
    _, industry = _names(facts)
    analogs = facts.get("analogs") or {}
    reason = _missing_reason(analogs)
    if reason is not None:
        return f"{FACT} 유사 사례(서울 전체 {industry}): {missing(reason)}"
    # 질문 속 상황 유형을 먼저, 운영자가 등록한 진행 중 유형을 뒤에
    categories = sorted(analogs.get("categories") or [], key=lambda c: c.get("reason") != "question")
    paragraphs = [p for p in (_category_paragraph(analogs, c.get("category")) for c in categories) if p]
    return "\n\n".join(paragraphs) or f"{FACT} 서울 전체 {industry}: 비교할 과거 사례가 없습니다."


# ── 그래도 한다면 ────────────────────────────────────────────


def hour_gap_sentence(bands: list[dict]) -> str | None:
    """어긋남 문장 — 프론트 `hourGapSentence`와 같은 규칙. gap 부호가 아니라 두 최대 구간의 위치로 말한다.

    동점은 앞 구간(원천 순서) — `max`는 첫 최대를 고른다.
    """
    if not bands:
        return None
    people = max(bands, key=lambda b: b["footfall_intensity"])["hour_band"]
    money = max(bands, key=lambda b: b["sales_intensity"])["hour_band"]
    if people == money:
        return f"사람과 돈이 {HOUR_BAND_LABELS.get(people, people)}에 같이 몰립니다."
    return f"사람은 {HOUR_BAND_LABELS.get(people, people)}에 가장 많고, 돈은 {HOUR_BAND_LABELS.get(money, money)}에 돕니다."


def _hours(hour_gap: dict, region: str, industry: str) -> str:
    if not hour_gap.get("available"):
        return f"{FACT} 시간대({region} {industry}): {missing(hour_gap.get('reason'))}"
    sentence = hour_gap_sentence(hour_gap.get("bands") or []) or missing("시간대 구간 없음")
    return f"{FACT} 시간대({region} 유동인구·{industry} 매출, {_quarter(hour_gap.get('year_quarter'))}): {sentence}"


def _profile(profile: dict, region: str) -> str:
    reason = _missing_reason(profile)
    if reason is not None:
        return f"{FACT} 동네 유형({region}): {missing(reason)}"
    return (
        f"{FACT} 동네 유형({region}, {_quarter(profile.get('year_quarter'))}): {profile.get('type_name')} — "
        f"{profile.get('type_reason')} 사람 흐름: {profile.get('time_label_name')} — 가장 많은 때 "
        f"{profile.get('peak_block_name')}, 가장 적은 때 {profile.get('trough_block_name')}."
    )


def _staying(change: dict, region: str) -> str:
    reason = _missing_reason(change)
    if reason is not None:
        return f"{FACT} 상권 영업 기간({region}): {missing(reason)}"
    seoul = change.get("seoul") or {}
    return (
        f"{FACT} 상권 영업 기간({region} 상권 전체·업종 무관, {_quarter(change.get('year_quarter'))}): "
        f"영업 중 점포 평균 {change['operating_months']:.0f}개월, 폐업 점포 평균 {change['closed_months']:.0f}개월 — "
        f"서울 동 상권 전체 기준값은 {seoul['operating_months']:.0f}개월·{seoul['closed_months']:.0f}개월입니다. "
        f"상권변화지표: {change.get('change_name')}."
    )


def _conditions(facts: dict) -> str:
    region, industry = _names(facts)
    lines = [
        _hours(facts.get("hour_gap") or {}, region, industry),
        _profile(facts.get("profile") or {}, region),
        _staying(facts.get("commerce_change") or {}, region),
        *([_BUDGET_LINE] if facts.get("budget") is not None else []),
    ]
    return "\n\n".join(lines)


# ── 대안 ─────────────────────────────────────────────────────


def _axis(items: list[dict] | None, name_key: str) -> list[str]:
    """한 축의 목록 — 순서 그대로 최대 3개, 등급 라벨 그대로. 비어 있으면 '대안 없음' 한 줄."""
    if not items:
        return ["- 대안 없음"]
    return [
        f"- {item.get(name_key)} ({_VERDICT_LABELS.get(item.get('verdict_code'), item.get('verdict_code'))})"
        for item in items[:_MAX_PER_AXIS]
    ]


def _alternatives(facts: dict) -> str:
    region, industry = _names(facts)
    alternatives = facts.get("alternatives") or {}
    if not alternatives.get("available"):
        return f"{FACT} 대안({region} {industry}): {missing(alternatives.get('reason'))}"
    return "\n".join(
        [
            f"{FACT} 같은 동네({region})의 다른 업종",
            *_axis(alternatives.get("industries"), "industry_name"),
            "",
            f"{FACT} 같은 업종({industry})의 다른 동네",
            *_axis(alternatives.get("regions"), "region_name"),
        ]
    )


# ── 지원사업 ─────────────────────────────────────────────────


def _due(candidate: dict) -> str:
    """마감일이 있으면 마감, 없으면 접수 기간 원문("예산 소진시까지"·"상시 접수")."""
    if candidate.get("deadline"):
        return f"마감 {candidate['deadline']}"
    return f"접수 {candidate.get('apply_period') or '기간 미상'}"


def _funding(facts: dict) -> str:
    region, industry = _names(facts)
    candidates = facts.get("funding_candidates")
    reason = _missing_reason(candidates)
    if reason is not None:
        return f"{FACT} 지원사업 후보({region} {industry}): {missing(reason)}\n\n{FUNDING_DISCLAIMER}"
    if not candidates:
        return f"{FACT} {region} {industry} 조건에 맞는 공고 후보가 없습니다.\n\n{FUNDING_DISCLAIMER}"
    # 공고 제목은 원문 그대로 「」에 담는다 — 링크·공고 번호는 화면 카드가 보여 준다
    lines = [f"- 「{c.get('title')}」 — {c.get('org')}, {_due(c)}" for c in candidates]
    head = (
        f"{FACT} {region} {industry} 조건으로 찾은 공고 후보입니다 — 자격 확정이 아니라 해당 가능성이며, "
        "지원 대상은 공고 원문에서 확인해야 합니다."
    )
    return "\n\n".join([head, "\n".join(lines), FUNDING_DISCLAIMER])


# 절 이름 → 작성 함수 (dict 디스패치)
_WRITERS = {
    "verdict": _verdict,
    "reasons": _reasons,
    "analogs": _analogs,
    "conditions": _conditions,
    "alternatives": _alternatives,
    "funding": _funding,
}


def build_sections(facts: dict) -> dict[str, str]:
    """facts → {절 이름: 마크다운}. `SECTION_TITLES` 순서, 절마다 `### 제목` 머리 + 본문."""
    return {name: f"### {title}\n\n{_WRITERS[name](facts)}" for name, title in SECTION_TITLES.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_report_sections.py -q`
Expected: `11 passed`

- [ ] **Step 5: 버전 로그 — v0.68.0 항목 열기**

`backend/docs/backend_ver_log.md`의 `# Backend Version Log` 바로 아래(기존 `## [v0.67.2]` 위)에 넣는다:

```markdown
## [v0.68.0] - 2026-10-05

### Added
- **리포트 코드 섹션 모듈** `apps/agent/domain/services/report_sections.py`(순수 모듈, 설계서 `docs/superpowers/specs/2026-10-05-report-code-first-design.md`) — 판정·왜 안 되나·유사 사례·그래도 한다면·대안 동네·업종·대안 업종 지원사업 6개 절을 facts만으로 쓴다(절 이름 → 작성 함수 dict 디스패치). 숫자마다 범위(동·업종 이름, "서울 동 상권 전체 기준값", "업종 무관", 분기)를 붙이고, 자료가 없으면 "자료 부족 — 이유"를 쓰며, 신뢰 태그(`[확인된 사실]`·`[참고 신호]`)는 코드가 붙인다. 시간대 문장 `hour_gap_sentence`는 프론트 `hour-gap-sentence.ts`와 같은 규칙(두 최대 구간의 위치)이며 같은 세 입력에 같은 문장을 내는지 테스트로 고정했다.
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/agent/domain/services/report_sections.py backend/tests/test_report_sections.py backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 리포트 6개 절을 facts로 쓰는 코드 섹션 모듈

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: 해석 단락 가드 — 숫자 문장 삭제 + `guard_answer`

**Files:**
- Modify: `backend/apps/agent/domain/services/report_guards.py` (import 1줄 + 파일 끝에 블록 추가)
- Modify: `backend/tests/test_report_guards.py` (import 2개 + 테스트 3개)
- Modify: `backend/docs/backend_ver_log.md` (v0.68.0 Added에 1줄)

**Interfaces:**
- Consumes: 같은 파일의 기존 `UrlStripper`(feed/flush, `events["links_stripped"]`), `verdict_contradiction(text, verdict_facts) -> str | None`
- Produces:
  - `drop_digit_sentences(text: str) -> tuple[str, int]` — (남은 단락, 지운 문장 수)
  - `@dataclass(frozen=True) GuardedAnswer(text: str, removed_sentences: int, links_stripped: int, contradiction: str | None)` + `ok` 프로퍼티(`contradiction is None and bool(text)`)
  - `guard_answer(raw: str, verdict_facts: dict | None) -> GuardedAnswer`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_report_guards.py` 맨 위 import 목록에서 `disclaimer_suffix,` 다음 줄에 두 이름을 넣는다:

```python
    disclaimer_suffix,
    drop_digit_sentences,
    guard_answer,
    guard_section,
```

파일 끝에 덧붙인다(`_RED`는 파일 위쪽에 이미 있다):

```python
# --- 해석(answer) 단락 숫자 가드 (2026-10-05 코드 우선 구조) ---


def test_숫자가_든_문장만_지우고_지운_수를_센다():
    assert drop_digit_sentences("폐업이 많습니다. 폐업률은 31%입니다. 대안을 보세요.") == ("폐업이 많습니다. 대안을 보세요.", 1)


def test_판정과_모순된_해석은_통과하지_못한다():
    got = guard_answer("판정은 **경고 없음**입니다. 해 볼 만합니다.", _RED)

    assert got.ok is False and got.contradiction == "판정은 **경고 없음"


def test_숫자_문장만_있던_해석은_가드_뒤_비어_통과하지_못한다():
    got = guard_answer("매출은 1,200만원입니다. 폐업률은 31%입니다.", _RED)

    assert (got.text, got.removed_sentences, got.ok) == ("", 2, False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_report_guards.py -q`
Expected: FAIL — `ImportError: cannot import name 'drop_digit_sentences'`

- [ ] **Step 3: Write minimal implementation**

`backend/apps/agent/domain/services/report_guards.py` — import 줄 `from collections.abc import Callable` 바로 아래에 `from dataclasses import dataclass`를 넣고, 파일 끝에 덧붙인다:

```python
# ── 해석(answer) 단락 가드 (설계서 2026-10-05-report-code-first §5) ────────

# 문장 끝 — 마침표·물음표·느낌표 뒤 공백. 한글 문장은 "~다."·"~요."로 끝나고, 소수점("3.5")은 뒤에 공백이 없어 갈리지 않는다.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_DIGIT = re.compile(r"\d")


def drop_digit_sentences(text: str) -> tuple[str, int]:
    """숫자가 든 문장을 통째로 지운다 — (남은 단락, 지운 문장 수). 숫자는 본문 6개 절이 범위와 함께 보여 준다."""
    sentences = [s for s in _SENTENCE_END.split(text.strip()) if s]
    kept = [s for s in sentences if not _DIGIT.search(s)]
    return " ".join(kept), len(sentences) - len(kept)


@dataclass(frozen=True)
class GuardedAnswer:
    """가드를 거친 해석 단락과 개입 기록 — 벤치가 그대로 남긴다."""

    text: str
    removed_sentences: int
    links_stripped: int
    contradiction: str | None

    @property
    def ok(self) -> bool:
        """화면에 낼 수 있는가 — 판정과 모순이 없고, 가드 뒤에도 글이 남았다."""
        return self.contradiction is None and bool(self.text)


def guard_answer(raw: str, verdict_facts: dict | None) -> GuardedAnswer:
    """해석 단락 통째 가드 — 링크·공고 번호 제거 → 판정 모순 검사 → 숫자 문장 삭제.

    모순은 단락 전체의 실패다(다음 모델로 넘긴다). 스트리밍하지 않으므로 끝까지 모은 글에 한 번 건다.
    """
    links = UrlStripper()
    text = links.feed(raw) + links.flush()
    contradiction = verdict_contradiction(text, verdict_facts)
    kept, removed = drop_digit_sentences(text)
    return GuardedAnswer(kept, removed, links.events["links_stripped"], contradiction)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_report_guards.py -q`
Expected: 기존 + 3개 모두 PASS (`62 passed`)

- [ ] **Step 5: 버전 로그**

`## [v0.68.0]`의 `### Added` 목록 끝에 한 줄:

```markdown
- **해석 단락 가드** `guard_answer`(`report_guards.py`) — LLM 해석(answer) 한 단락에 링크·공고 번호 제거(`UrlStripper`) → 판정 모순 검사(`verdict_contradiction`, 모순이면 단락 전체 실패) → 숫자가 든 문장 삭제(`drop_digit_sentences`, 문장 끝 `.!?` + 공백 기준)를 차례로 건다. 결과 `GuardedAnswer`는 지운 문장 수·지운 링크 수·모순 구절을 남긴다(벤치 지표).
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/agent/domain/services/report_guards.py backend/tests/test_report_guards.py backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 해석 단락 가드 — 숫자 문장 삭제·판정 모순 실패

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 인터랙터 재배선 — 코드 절 즉시 방출 + 해석 한 단락, 도구 루프 제거

**Files:**
- Replace: `backend/apps/agent/app/use_cases/analysis_interactor.py` (전체 교체)
- Modify: `backend/apps/agent/dependencies/analysis_dependencies.py`
- Modify: `backend/apps/agent/domain/services/section_stream.py:17-19` (`SECTION_ORDER`)
- Modify: `backend/apps/agent/domain/entities/agent_event_entity.py:14-15` (docstring)
- Replace: `backend/tests/test_agent_loop.py` (전체 교체)
- Modify: `backend/tests/test_agent_section_stream.py` (순서 상수 테스트 1개)
- Modify: `backend/tests/test_agent_router.py` (저장 순서 테스트 1개)
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 1 `SECTION_TITLES`, `build_sections(facts)`; Task 2 `guard_answer(raw, verdict_facts) -> GuardedAnswer`; 기존 `concat_sections(chunks, order=...)`, `ReportFactsCollector.collect(region, industry, budget, question)`, `LLMGatewayPort.chat(messages, tools) -> LLMTurn`
- Produces (Task 4가 쓴다):
  - `ANSWER_FALLBACK: str` = `"질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요."`
  - `SYSTEM_PROMPT: str` (해석 전용, 짧게)
  - `answer_message(facts: dict, question: str | None, sections: dict[str, str]) -> str`
  - `AnalysisInteractor(llm: LLMGatewayPort, facts: ReportFactsCollector, budget: int | None = None, retry_llm: LLMGatewayPort | None = None)` — `tools`·`now` 인자 없음
  - `AnalysisInteractor.last_usage: LLMUsage`, `AnalysisInteractor.last_answer_attempts: list[dict]` — 시도마다 `{"model", "raw", "removed_sentences", "links_stripped", "contradiction"}` 또는 `{"model", "error"}`
  - `section_stream.SECTION_ORDER == ("answer", "verdict", "reasons", "analogs", "conditions", "alternatives", "funding")`
- 이 태스크가 지우는 이름(`_SECTIONS`, `_fallback_section`, `guarded_fallback_section`, `check_arguments`, `_FINAL_REQUEST` 등)을 벤치(`benchmark_report.py`)가 아직 import한다 — **Task 4가 고칠 때까지 `tests/test_report_bench_cli.py`는 import 오류가 난다.** 이 태스크의 테스트 실행은 그 파일을 `--ignore`한다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_agent_loop.py`를 아래로 통째로 바꾼다(옛 도구 루프·프롬프트 계약 테스트는 대상 코드와 함께 사라진다):

```python
"""analysis_interactor — 사실은 코드, 해석은 LLM 한 단락: SSE 이벤트 계약 (FakeLLM, DB·네트워크 없음)."""

import json
from pathlib import Path

from apps.agent.app.ports.output.agent_port import LLMGatewayPort, LLMTurn, LLMUsage
from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK, SYSTEM_PROMPT, AnalysisInteractor
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.report_sections import SECTION_TITLES, build_sections

# 평가셋 고정 facts — 송정동 한식, 판정 red(비추천)
_FACTS = json.loads(
    (Path(__file__).resolve().parents[2] / "data/eval/report_facts_150/e001.json").read_text(encoding="utf-8")
)
_ANSWER = "이 동네 한식은 문을 닫는 가게가 여는 가게보다 많습니다. 서두르기보다 대안 업종을 먼저 보세요."

_SIGNATURE_FIELDS = {
    "agent_status": ("agent", "status"),
    "facts": (),
    "report_delta": ("section",),
    "report_done": (),
}


def _signature(event: AgentEvent) -> tuple:
    """이벤트를 (type, 식별 필드…) 튜플로 축약 — 순서 계약 비교용."""
    return (event.type, *(event.payload[field] for field in _SIGNATURE_FIELDS[event.type]))


class FakeLLM(LLMGatewayPort):
    """답 스크립트를 순서대로 돌려주는 대역 — 예외를 넣으면 그 호출에서 던진다. 호출 인자를 기록한다."""

    def __init__(self, replies: list, model_name: str = "fake-llm") -> None:
        self.model_name = model_name
        self._replies = list(replies)
        self.calls: list[tuple[list[dict], list]] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMTurn(text=reply, tool_calls=[], usage=LLMUsage(input_tokens=30, output_tokens=7))

    def stream(self, messages, tools):
        raise AssertionError("해석은 모았다가 한 번에 낸다 — stream을 쓰지 않는다")


class FakeFactsCollector(ReportFactsCollector):
    """수집 결과를 고정하는 대역 (포트 조립 없이)."""

    def __init__(self) -> None:
        pass

    def collect(self, region, industry, budget=None, question=None) -> dict:
        return _FACTS


def _run(llm, question=None, retry_llm=None) -> tuple[AnalysisInteractor, list[AgentEvent]]:
    interactor = AnalysisInteractor(llm=llm, facts=FakeFactsCollector(), retry_llm=retry_llm)
    return interactor, list(interactor.run("1120072000", "korean_food", question))


def _deltas(events: list[AgentEvent]) -> dict[str, str]:
    return {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}


def test_이벤트_순서는_사실_코드_여섯_절_해석_완료다():
    _, events = _run(FakeLLM([_ANSWER]))

    assert [_signature(e) for e in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "facts", "running"),
        ("facts",),
        ("agent_status", "facts", "done"),
        ("agent_status", "writer", "running"),
        *(("report_delta", name) for name in SECTION_TITLES),
        ("report_delta", "answer"),
        ("agent_status", "writer", "done"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    deltas = _deltas(events)
    assert {name: deltas[name] for name in SECTION_TITLES} == build_sections(_FACTS)
    assert deltas["answer"] == _ANSWER


def test_LLM에는_사실_JSON이_아니라_질문과_코드가_쓴_절만_간다():
    llm = FakeLLM([_ANSWER])

    _run(llm, question="여기서 한식 해도 될까요?")

    [(messages, tools)] = llm.calls
    user = messages[1]["content"]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert tools == []
    assert "사용자 질문: 여기서 한식 해도 될까요?" in user
    assert build_sections(_FACTS)["reasons"] in user
    assert '"verdict_code"' not in user  # 원본 facts JSON은 넘기지 않는다


def test_질문이_없으면_총평을_요청한다():
    llm = FakeLLM([_ANSWER])

    _run(llm)

    assert "총평" in llm.calls[0][0][1]["content"]


def test_숫자가_든_문장은_해석에서_지운다():
    _, events = _run(FakeLLM(["폐업이 개업보다 많습니다. 폐업률은 31%입니다. 대안 업종을 먼저 보세요."]))

    assert _deltas(events)["answer"] == "폐업이 개업보다 많습니다. 대안 업종을 먼저 보세요."


def test_판정과_모순되면_다음_모델이_다시_쓴다():
    first = FakeLLM(["판정은 **경고 없음**입니다. 해 볼 만합니다."], "gemini-2.5-flash")
    second = FakeLLM([_ANSWER], "gemma4:12b")

    interactor, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == _ANSWER
    assert [a["model"] for a in interactor.last_answer_attempts] == ["gemini-2.5-flash", "gemma4:12b"]
    assert interactor.last_answer_attempts[0]["contradiction"] == "판정은 **경고 없음"


def test_모든_모델이_실패하면_코드_한_줄로_맺는다():
    first = FakeLLM([RuntimeError("429")], "gemini-2.5-flash")
    second = FakeLLM(["매출은 1,200만원입니다."], "gemma4:12b")  # 가드 뒤 빈 단락

    interactor, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == ANSWER_FALLBACK
    assert events[-1].type == "report_done"
    assert interactor.last_answer_attempts[0]["error"] == "RuntimeError: 429"


def test_첫_모델이_이미_로컬로_답했으면_로컬을_다시_부르지_않는다():
    """hybrid가 Gemini 장애로 로컬에 내려갔다면 model_name이 같다 — 온도 0이라 다시 불러도 같은 답이다."""
    first = FakeLLM(["판정은 **경고 없음**입니다."], "gemma4:12b")
    second = FakeLLM([], "gemma4:12b")

    _, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == ANSWER_FALLBACK and second.calls == []


def test_인용은_사실_묶음의_뉴스로_만든다():
    _, events = _run(FakeLLM([_ANSWER]))

    first_news = _FACTS["news"][0]
    assert events[-1].payload["citations"][0] == {
        "title": first_news["content"].split("\n")[0],
        "url": first_news["url"],
        "grade": "signal",
    }


def test_시스템_프롬프트가_숫자와_등급_변경과_추정을_금지한다():
    for phrase in ("3~5문장", "숫자를 쓰지 않는다", "판정 등급을 바꾸거나", "자료가 부족해 판단할 수 없다", "대출 중개"):
        assert phrase in SYSTEM_PROMPT


def test_운영_hybrid만_로컬_재시도를_붙인다():
    from apps.agent.dependencies.analysis_dependencies import build_analysis_use_case

    assert build_analysis_use_case("hybrid")._retry_llm.model_name == "gemma4:12b"
    assert build_analysis_use_case("gemma3")._retry_llm is None
```

`backend/tests/test_agent_section_stream.py`의 마지막 테스트를 바꾼다:

```python
# 이전
def test_섹션_순서_상수는_인터랙터_계약과_같다():
    """두 벌이 어긋나면 저장 순서와 방출 순서가 갈린다."""
    from apps.agent.app.use_cases.analysis_interactor import _SECTIONS

    assert tuple(name for name, _ in _SECTIONS) == SECTION_ORDER

# 이후
def test_섹션_순서_상수는_해석_다음_코드_절_순서다():
    """두 벌이 어긋나면 저장 순서와 방출 순서가 갈린다 — 해석은 늦게 오지만 저장본은 맨 위다."""
    from apps.agent.domain.services.report_sections import SECTION_TITLES

    assert SECTION_ORDER == ("answer", *SECTION_TITLES)
```

`backend/tests/test_agent_router.py`의 `test_저장되는_report_md는_조각을_섹션별로_이어_붙인_글이다`에서 `_ChunkedUseCase.run`의 `reasons` 줄 다음에 해석 조각을 넣고, 기대값 맨 앞에 해석을 넣는다:

```python
            yield AgentEvent("report_delta", {"section": "reasons", "markdown": "폐업률이 높다."})
            yield AgentEvent("report_delta", {"section": "answer", "markdown": "해석."})  # 해석은 맨 끝에 온다
            yield AgentEvent("report_done", {"report_id": "x", "citations": []})
```

```python
    assert saved["report_md"] == "해석.\n\n🔴 비추천.\n\n폐업률이 높다.\n\n공고 2건."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_agent_loop.py tests/test_agent_section_stream.py tests/test_agent_router.py -q`
Expected: FAIL — `ImportError: cannot import name 'ANSWER_FALLBACK'`(test_agent_loop), `SECTION_ORDER` 불일치, 저장 순서 불일치

- [ ] **Step 3: Write minimal implementation**

`backend/apps/agent/app/use_cases/analysis_interactor.py`를 통째로 바꾼다:

```python
"""AnalysisInteractor — 리포트 SSE 이벤트 제너레이터 (사실은 코드, 해석은 LLM 한 단락).

설계서 docs/superpowers/specs/2026-10-05-report-code-first-design.md.
`app/` 레이어이므로 FastAPI·SQLAlchemy·어댑터를 import하지 않는다.

순서: 사실 수집(`facts`) → 코드가 facts로 쓴 6개 절을 곧바로 `report_delta`로 → LLM 해석(`answer`) 한 단락을
끝까지 모아 가드(링크 제거·판정 모순 검사·숫자 문장 삭제)를 거쳐 한 번에 → `report_done`.
가드에 걸리거나 호출이 실패하면 다음 모델(`retry_llm`)로, 그래도 안 되면 코드 한 줄(`ANSWER_FALLBACK`)로 맺는다.
도구 루프는 없다 — 평가 252회에서 도구 호출 0회였고, 자금 계획은 별도 화면이다.
"""

import logging
import uuid
from collections.abc import Iterator

from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import LLMGatewayPort, LLMUsage
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.report_guards import guard_answer
from apps.agent.domain.services.report_sections import SECTION_TITLES, build_sections
from apps.agent.domain.services.section_stream import concat_sections

LOGGER = logging.getLogger("beyondfacade.agent.loop")

ANSWER_FALLBACK = "질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요."

SYSTEM_PROMPT = """당신은 서울 창업 경고 리포트 맨 위의 "해석" 한 단락을 쓴다.
사용자 메시지에 질문(없으면 총평 요청)과, 화면에 이미 나간 리포트 본문 6개 절이 주어진다.
본문은 코드가 사실에서 쓴 글이다 — 본문만 근거로 삼는다.

[출력 규칙]
- 3~5문장, 한 단락. 제목·목록·표·굵은 글씨를 쓰지 않는다.
- 질문이 있으면 첫 문장에서 질문에 직접 답한다. 질문이 없으면 이 동네에서 이 업종을 한다면 먼저 볼 것을 총평한다.
- 숫자를 쓰지 않는다 — 아라비아 숫자는 한 글자도 쓰지 않는다. 숫자는 본문이 범위와 함께 보여 준다.
  링크·공고 번호도 쓰지 않는다.
- 판정 등급을 바꾸거나 새로 매기지 않는다. 본문에 없는 사실을 보태지 않는다.
- 본문이 "자료 부족"이라고 한 곳은 추정으로 메우지 않고 "자료가 부족해 판단할 수 없다"고 말한다.

[응답 규칙]
① 외국인 관련 내용은 업종 타깃 정합성 문맥으로만 쓴다. 비하·차별 표현은 금지한다.
② 2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 지연되어 왜곡되었을 수 있음을 감안한다.
③ 대출 중개와 특정 은행·상품 추천은 금지한다. 금리·한도를 말하면 "예상치"라고 밝힌다."""

_NO_QUESTION = "질문 없음 — 이 동네에서 이 업종을 한다면 먼저 볼 것을 총평하라."


def answer_message(facts: dict, question: str | None, sections: dict[str, str]) -> str:
    """해석 LLM의 사용자 메시지 — 질문과 화면에 나간 6개 절 그대로. 원본 facts JSON은 넘기지 않는다(설계서 §5)."""
    region = facts.get("region") or {}
    return "\n".join(
        [
            f"분석 지역: {region.get('name')} / 업종: {region.get('industry_name')}",
            f"사용자 질문: {question}" if question else _NO_QUESTION,
            "[리포트 본문]",
            concat_sections(sections.items(), order=SECTION_TITLES),
        ]
    )


def _news_citations(news: object) -> list[dict]:
    """facts.news → 참고 신호 인용 {title, url, grade}. 제목은 기사 첫 줄, 링크 없는 기사는 뺀다(같은 링크는 한 번).

    수집이 실패한 자리는 `{"available": False, ...}` dict라 목록일 때만 읽는다.
    """
    citations: dict[str, dict] = {}
    for hit in news if isinstance(news, list) else []:
        url = hit.get("url")
        if url:
            title = (hit.get("content") or "").split("\n")[0] or url
            citations.setdefault(url, {"title": title, "url": url, "grade": "signal"})
    return list(citations.values())


class AnalysisInteractor(AnalysisUseCase):
    def __init__(
        self,
        llm: LLMGatewayPort,
        facts: ReportFactsCollector,
        budget: int | None = None,
        retry_llm: LLMGatewayPort | None = None,
    ) -> None:
        self._llm = llm
        self._facts = facts
        self._budget = budget  # facts 수집에 그대로 넘긴다(facts.budget)
        self._retry_llm = retry_llm  # 해석이 가드에 걸리거나 호출이 실패하면 다음 모델 (운영 hybrid: 로컬)
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)
        # 직전 실행의 해석 시도 기록(모델별 원문·지운 문장 수·링크 수·모순·오류) — 벤치가 남겨 채점한다
        self.last_answer_attempts: list[dict] = []

    def myself(self) -> dict:
        return {
            "analysis_id": "myself",
            "region_code": "myself",
            "industry": "myself",
            "model": getattr(self._llm, "model_name", "gemma3"),
        }

    def run(self, region: str, industry: str, question: str | None) -> Iterator[AgentEvent]:
        report_id = uuid.uuid4().hex
        self.last_usage = LLMUsage(input_tokens=0, output_tokens=0)
        self.last_answer_attempts = []
        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"})

        yield AgentEvent("agent_status", {"agent": "facts", "status": "running"})
        facts = self._facts.collect(region, industry, self._budget, question)
        yield AgentEvent("facts", {"facts": facts})  # 프론트 계약은 중첩이다
        yield AgentEvent("agent_status", {"agent": "facts", "status": "done"})

        yield AgentEvent("agent_status", {"agent": "writer", "status": "running"})
        sections = build_sections(facts)
        for name, markdown in sections.items():  # 본문은 사실이 모이자마자 나간다
            yield AgentEvent("report_delta", {"section": name, "markdown": markdown})
        answer = self._answer(facts, question, sections)
        yield AgentEvent("report_delta", {"section": "answer", "markdown": answer})
        yield AgentEvent("agent_status", {"agent": "writer", "status": "done"})
        yield AgentEvent("agent_status", {"agent": "orchestrator", "status": "done"})
        yield AgentEvent("report_done", {"report_id": report_id, "citations": _news_citations(facts.get("news"))})

    def _answer(self, facts: dict, question: str | None, sections: dict[str, str]) -> str:
        """해석 한 단락 — 모델을 차례로 시도해 가드를 통과한 첫 단락, 없으면 코드 한 줄."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": answer_message(facts, question, sections)},
        ]
        for llm in self._answer_models():
            answer = self._attempt(llm, messages, facts.get("verdict"))
            if answer:
                return answer
        return ANSWER_FALLBACK

    def _answer_models(self) -> Iterator[LLMGatewayPort]:
        """시도할 모델 — 첫 모델이 실제로 답한 모델과 같은 다음 모델은 건너뛴다(온도 0이라 같은 답이다).

        hybrid는 Gemini 장애 때 이미 로컬로 내려가 `model_name`이 로컬 이름이 된다 — 그래서 첫 시도 뒤에 비교한다.
        """
        yield self._llm
        if self._retry_llm is not None and self._retry_llm.model_name != self._llm.model_name:
            yield self._retry_llm

    def _attempt(self, llm: LLMGatewayPort, messages: list[dict], verdict: dict | None) -> str | None:
        """한 모델 1회 — 가드를 통과한 단락, 아니면 None. 시도마다 기록을 남긴다."""
        try:
            turn = llm.chat(messages, [])
        except Exception as error:  # 장애로 리포트를 끊지 않는다 — 다음 모델 또는 코드 한 줄로 맺는다
            LOGGER.warning("해석 생성 실패 — %s: %s", llm.model_name, type(error).__name__)
            self.last_answer_attempts.append({"model": llm.model_name, "error": f"{type(error).__name__}: {error}"})
            return None
        self._accumulate(turn.usage)
        guarded = guard_answer(turn.text, verdict)
        self.last_answer_attempts.append(
            {
                "model": llm.model_name,
                "raw": turn.text,
                "removed_sentences": guarded.removed_sentences,
                "links_stripped": guarded.links_stripped,
                "contradiction": guarded.contradiction,
            }
        )
        if guarded.contradiction:
            LOGGER.info("해석이 판정과 모순 — %s: %s", llm.model_name, guarded.contradiction[:60])
        return guarded.text if guarded.ok else None

    def _accumulate(self, usage: LLMUsage) -> None:
        self.last_usage = LLMUsage(
            input_tokens=self.last_usage.input_tokens + usage.input_tokens,
            output_tokens=self.last_usage.output_tokens + usage.output_tokens,
        )
```

`backend/apps/agent/dependencies/analysis_dependencies.py`:

1. import 두 줄을 지운다: `from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway`, `from apps.agent.app.use_cases.agent_tools import build_tools`
2. `_LLM_REGISTRY` 정의 바로 아래에 추가:

```python

# 해석이 가드에 걸리면(판정 모순·숫자만 남은 단락) 다음 모델 — 운영 hybrid만 로컬로 한 번 더 쓴다(설계서 §5).
# 단일 모델 직접 지정(벤치·run_agent_eval)은 그 모델만 평가한다.
_RETRY_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {"hybrid": _local}
```

3. `build_analysis_use_case`의 docstring 둘째 단락과 본문(모델 조회 `try` 블록 다음)을 바꾼다:

```python
def build_analysis_use_case(model: str = "hybrid", budget: int | None = None) -> AnalysisUseCase:
    """요청 스코프 AnalysisInteractor — last_usage 누적이 요청 간에 섞이지 않게.

    세션 예산(원)은 facts 수집기에 심는다 — `facts.budget`이다(그래도 한다면 절의 자금 계획 안내).
    """
    try:
        llm_factory = _LLM_REGISTRY[model]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델: {model}") from error
    facts = ReportFactsCollector(
        region_facts=RegionFactsGateway(),
        verdict_facts=VerdictFactsGateway(),
        funding_facts=FundingFactsGateway(),
        news_search=get_rag_search_use_case(),
        analog_facts=EventAnalogFactsGateway(),
    )
    retry = _RETRY_REGISTRY.get(model)
    return AnalysisInteractor(
        llm=llm_factory(), facts=facts, budget=budget, retry_llm=retry() if retry else None
    )
```

`backend/apps/agent/domain/services/section_stream.py`의 `SECTION_ORDER`와 그 위 주석 두 줄을 바꾼다:

```python
# 저장·표시 기준 섹션 순서 — 맨 위 해석(answer) 다음에 코드 6개 절(report_sections.SECTION_TITLES 순서).
# 해석은 6개 절보다 늦게 도착하지만 저장본은 화면처럼 맨 위다. answer 없는 옛 저장본은 그대로다.
SECTION_ORDER = ("answer", "verdict", "reasons", "analogs", "conditions", "alternatives", "funding")
```

`backend/apps/agent/domain/entities/agent_event_entity.py` docstring의 report_delta 두 줄을 바꾼다:

```python
    - report_delta : {section, markdown}    section ∈ answer|verdict|reasons|analogs|conditions|alternatives|funding
                                            코드 6개 절이 먼저 한 조각씩, 해석(answer)이 마지막에 한 조각 온다(프론트는 append)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/ -q --ignore=tests/test_report_bench_cli.py`
Expected: 전부 PASS. (`test_report_bench_cli.py`는 Task 4까지 import 오류 — 여기서는 제외한다. `report_fallback.py`·`SectionSplitter`·도구 정의와 그 테스트는 아직 남아 있고 통과한다 — Task 5가 정리.)

- [ ] **Step 5: 버전 로그**

`## [v0.68.0]`에 `### Changed`·`### Removed` 절을 만들어(없으면) 아래를 넣는다:

```markdown
### Changed
- **리포트 구조: 사실은 코드, 해석은 LLM 한 단락** (`analysis_interactor.py` 전면 교체) — 사실 수집 직후 코드가 쓴 6개 절을 `report_delta`(절당 한 조각)로 곧바로 내보내고, LLM은 맨 위 해석(`answer`) 한 단락(3~5문장, 숫자·링크·공고 번호 금지, 질문이 없으면 총평)만 쓴다. 해석 입력은 원본 facts JSON이 아니라 질문 + 코드가 쓴 6개 절 그대로(약 14k → 2k 토큰대). 해석은 비스트리밍 `chat()`으로 끝까지 받아 `guard_answer`를 거쳐 한 번에 내보낸다. 판정 모순·가드 뒤 빈 단락·호출 실패면 다음 모델로 넘기고(운영 hybrid: Gemini → 로컬 gemma4:12b, `_RETRY_REGISTRY`; 첫 모델이 이미 로컬로 답했으면 같은 모델을 다시 부르지 않는다), 그래도 안 되면 코드 한 줄 "질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요."로 맺는다. 시도 기록은 `last_answer_attempts`.
- SSE 순서: `agent_status`·`facts` → 코드 6개 절 → `answer` → `report_done`. 인용은 `facts.news`로 코드가 만든 참고 신호(제목 = 기사 첫 줄, 링크 없는 기사 제외)만.
- 저장 순서 `SECTION_ORDER`에 `answer`를 맨 앞에 — 저장 리포트(`report_md`)도 화면처럼 해석이 맨 위다. answer 없는 옛 저장본은 그대로다.

### Removed
- 리포트 경로의 도구 루프(턴 한도·벽시계 예산·`_FINAL_REQUEST`·도구 인자 검사·재프롬프트·도구 인용·스테이지 개폐) — 평가 252회에서 도구 호출 0회였고 자금 계획은 별도 화면이다. 옛 6개 절 시스템 프롬프트와 LLM 절 폴백(`_fallback_section`·`guarded_fallback_section`)도 함께.
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/agent/app/use_cases/analysis_interactor.py backend/apps/agent/dependencies/analysis_dependencies.py backend/apps/agent/domain/services/section_stream.py backend/apps/agent/domain/entities/agent_event_entity.py backend/tests/test_agent_loop.py backend/tests/test_agent_section_stream.py backend/tests/test_agent_router.py backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 리포트 코드 절 즉시 방출 + 해석 한 단락, 도구 루프 제거

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: 벤치 — 해석 단락 채점·코드 절 자동 검사·해석 판정 묶음

**Files:**
- Modify: `backend/apps/agent/adapter/inbound/cli/benchmark_report.py`
- Modify: `backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py`
- Create: `data/eval/report_answer_rubric.md`
- Modify: `backend/tests/test_report_bench_cli.py`, `backend/tests/test_report_bench_scoring.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 1 `build_sections(facts)`; Task 3 `ANSWER_FALLBACK`, `AnalysisInteractor(llm=, facts=)`, `.last_answer_attempts`, `.last_usage`; 기존 `contradicts_verdict(text, verdict_facts) -> bool`(report_guards), `check_rule_keywords`, `_tokens`(report_bench_scoring 내부), `concat_sections`
- Produces (Task 7이 쓴다):
  - CLI 명령 `sections-check` → `<runs>/sections_check.json` `{"scenarios": N, "issues": {id: {"unscoped": [...], "missing": [...]}}}`
  - `score_run(record: dict, facts: dict) -> dict` 키 `complete, fallback, verdict_ok, digits, removed_sentences, raw_contradiction, rule_hits`
  - `score_summary(model: str, runs: list[dict]) -> dict` — evaluate 호환 키(`completion`·`verdict_match`·`fabrication`=가드 뒤 숫자가 남은 해석 비율·`rule_violations_keyword`·`first_p95_ms`=해석 단락 시각·`total_p95_ms`) + `answer: {fallback_rate, digits_after_guard, raw_contradiction_rate, removed_sentences}` + `sampling` + `runs`
  - `run_record(scenario_id, rep, got, error, interactor) -> dict` — `answer_attempts` 포함, `tool_results`·`raw_sections`·`guard` 없음
  - `judge-export`(비교 모드 아님) → `packet_<id>.md`(질문 + 코드 본문 한 벌 + 가린 해석들), `mapping.json`, `human_sample.json`(시드 0으로 고른 20건)
  - report_bench_scoring: `SCOPE_WORDS`, `unscoped_number_lines(markdown, scope_words, names=()) -> list[str]`, `missing_data_gaps(facts, sections) -> list[str]`, `ANSWER_RUBRIC_PATH`, `answer_packets(scenario_id, question, body, answers, seed) -> tuple[str, dict[str, str]]`
- 비교 모드(`--compare-tag`)·`evaluate`·`render_llm_report`는 그대로 둔다(이번 평가에 쓰지 않는다 — 요약이 호환 키를 유지해 깨지지 않는다). `report_bench_scoring`의 기존 함수(숫자 대조·일관성 등)는 옛 캐시 재채점용 라이브러리로 남긴다.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_report_bench_scoring.py` 파일 끝에 덧붙인다:

```python
# --- 코드 절 자동 검사·해석 판정 묶음 (v0.68.0 코드 우선 구조) ---


def test_범위_낱말_없이_숫자만_있는_줄을_찾는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import unscoped_number_lines

    markdown = "\n".join([
        "[확인된 사실] 송정동 한식 연간 폐업률: 2019년 2.8% → 2025년 19.1%.",  # 범위 있음
        "영업 중 점포 평균 124개월.",  # 범위 없음
        "- 「2026년 3천만원 지원 공고」 — 중소벤처기업부, 마감 2026-10-07",  # 공고 제목 속 숫자는 세지 않는다
        "- 상계3.4동 (경고 없음)",  # 숫자가 든 동 이름
    ])

    assert unscoped_number_lines(markdown, ["송정동", "한식", "서울"], ["상계3.4동"]) == ["영업 중 점포 평균 124개월."]


def test_자료가_없는데_이유가_적히지_않은_자리를_찾는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import missing_data_gaps

    facts = {
        "hour_gap": {"available": False, "reason": "시간대 자료 없음"},
        "profile": {"available": False, "reason": "프로필 없음"},
        "verdict": {"available": True, "signals": [{"key": "survival_cliff", "level": "unavailable", "evidence": "표본 부족 — 1곳"}]},
    }
    sections = {name: "" for name in ("verdict", "reasons", "analogs", "conditions", "alternatives", "funding")}
    sections["conditions"] = "시간대: 자료 부족 — 시간대 자료 없음"

    assert missing_data_gaps(facts, sections) == ["profile", "signal:survival_cliff"]


def test_해석_판정_묶음은_본문_한_벌과_가린_해석을_싣는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import answer_packets

    packet, mapping = answer_packets("e001", None, "### 판정\n\n본문", {"m1": "해석 하나.", "m2": "해석 둘."}, 0)

    assert sorted(mapping.values()) == ["m1", "m2"]
    assert packet.count("### 판정") == 1 and "질문: (없음 — 총평)" in packet
    assert "해석 하나." in packet and "해석 둘." in packet and "m1" not in packet
```

`backend/tests/test_report_bench_cli.py`:

1. import 줄 `from apps.agent.app.use_cases.analysis_interactor import SYSTEM_PROMPT`를 지운다.
2. `_events()`와 `test_이벤트에서_지연과_절을_모은다`를 아래로 바꾸고, 바로 뒤에 새 채점 테스트를 둔다:

```python
def _events():
    return [
        AgentEvent("agent_status", {"agent": "facts", "status": "running"}),
        AgentEvent("facts", {"verdict": {}}),
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n비추천"}),
        AgentEvent("report_delta", {"section": "answer", "markdown": "신중히 보세요."}),
        AgentEvent("report_done", {"report_id": "r", "citations": []}),
    ]


def test_첫_글자_지연은_해석_단락이_나온_시각이다():
    ticks = iter([10.0, 10.5, 12.0])  # facts 수신 · 해석 delta · done (초) — 코드 절 delta는 시계를 읽지 않는다
    got = collect_run(_events(), clock=lambda: next(ticks))
    assert got["first_ms"] == 500 and got["total_ms"] == 2000
    assert got["sections"] == {"verdict": "### 판정\n비추천", "answer": "신중히 보세요."}


def test_해석_채점은_가드_뒤_숫자_모순_폴백과_지운_문장을_센다():
    from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK

    facts = {"verdict": {"available": True, "verdict_code": "red"}}
    attempts = [{"model": "a", "removed_sentences": 2, "contradiction": "판정은 **경고 없음"},
                {"model": "b", "removed_sentences": 1, "contradiction": None}]

    ok = score_run({"sections": {"answer": "신중히 보세요. 대안을 먼저 보세요."}, "answer_attempts": attempts,
                    "error": None}, facts)
    fallback = score_run({"sections": {"answer": ANSWER_FALLBACK}, "error": None}, facts)

    assert ok == {"complete": True, "fallback": False, "verdict_ok": True, "digits": 0, "removed_sentences": 3,
                  "raw_contradiction": True, "rule_hits": []}
    assert fallback["fallback"] is True and fallback["removed_sentences"] == 0
```

3. 아래 테스트 함수를 통째로 지운다(대상 함수 `score_record`·`guard_summary`·`_written_sections`·도구/프롬프트 숫자 근거가 사라진다): `test_한_회차_채점_완주_판정_숫자`, `test_도구_결과와_질문에만_있는_숫자는_지어낸_것이_아니다`, `test_판정_절을_LLM이_안_썼으면_판정_일치는_거짓`, `test_시스템_프롬프트에_있는_숫자는_지어낸_것이_아니다`, `test_한_회차_채점은_판정_절에_등급_말이_있는지_남긴다`, `test_가드를_씌운_폴백_절도_LLM이_쓴_절로_세지_않는다`, `test_회차_기록에_가드_전_원문과_개입_횟수를_남긴다`, `test_채점은_가드_전_원문도_따로_매기고_옛_캐시는_화면_본문으로_대신한다`, `test_모델_요약에_가드_개입_합계와_원문_지표를_싣는다`, `test_가드_기록이_없는_옛_캐시는_개입_표를_싣지_않는다`. (`_GUARD` 상수와 `test_보고서에_가드_개입_표와_첫_글자_지연_주의를_싣는다`는 `render_llm_report`용이라 남긴다.)
4. `test_회차_기록에_온도와_seed를_남긴다`를 아래로 바꾼다:

```python
def test_회차_기록에_해석_시도와_온도와_seed를_남긴다():
    from types import SimpleNamespace

    from apps.agent.adapter.inbound.cli.benchmark_report import run_record
    from apps.agent.app.ports.output.agent_port import LLMUsage
    from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE

    attempts = [{"model": "m", "raw": "원문", "removed_sentences": 1, "links_stripped": 0, "contradiction": None}]
    interactor = SimpleNamespace(last_usage=LLMUsage(input_tokens=3, output_tokens=4), last_answer_attempts=attempts)
    row = run_record("s01", 0, {"sections": {"answer": "해석"}}, None, interactor)

    assert (row["temperature"], row["seed"]) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert row["answer_attempts"] == attempts and row["sections"] == {"answer": "해석"}
    assert row["usage"] == {"input_tokens": 3, "output_tokens": 4}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/test_report_bench_cli.py tests/test_report_bench_scoring.py -q`
Expected: FAIL — `ImportError: cannot import name '_SECTIONS'`(benchmark_report가 Task 3에서 사라진 이름을 import), scoring의 `ImportError: cannot import name 'unscoped_number_lines'`

- [ ] **Step 3: Implement — `report_bench_scoring.py`**

1. 모듈 docstring 둘째 줄 `숫자 지어내기 대조, 판정 일치, LLM 작성 절 판별, 블라인드 판정자 묶음.` 다음에 한 줄 추가: `v0.68.0: 코드 절 자동 검사(범위 없는 숫자 줄·이유 빠진 자료 부족 자리)와 해석(answer) 판정 묶음.`
2. `from collections.abc import Callable` → `from collections.abc import Callable, Iterable`
3. `RUBRIC_PATH = ...` 다음 줄에: `ANSWER_RUBRIC_PATH = "data/eval/report_answer_rubric.md"  # 해석 단락 판정 기준(v0.68.0)`
4. `# ── 블라인드 판정자 묶음 ───` 머리 **바로 위**에 넣는다:

```python
# ── 코드 절 자동 검사 (설계서 2026-10-05-report-code-first §7) ──

# 줄에 이 낱말이나 동·업종 이름이 있으면 숫자에 범위가 붙은 것으로 본다
SCOPE_WORDS = ("서울", "전국", "동 전체", "업종 무관", "최근")
_QUOTED = re.compile(r"「[^」]*」")  # 공고 제목 원문 — 제목 속 숫자는 주장이 아니다


def unscoped_number_lines(markdown: str, scope_words: Iterable[str], names: Iterable[str] = ()) -> list[str]:
    """사실값 숫자가 있는데 범위 낱말이 하나도 없는 줄.

    숫자 토큰은 지어내기 대조와 같은 규칙(`_tokens` — 단위 없는 10 이하 정수·연도는 버린다)이다.
    공고 제목(「」)과 이름(숫자가 든 동 이름 "상계3.4동")은 숫자로 세지 않는다.
    """
    scope, names = tuple(scope_words), tuple(names)
    out: list[str] = []
    for line in markdown.splitlines():
        text = _QUOTED.sub("", line)
        for name in names:
            text = text.replace(name, "")
        if _tokens(text) and not any(word in line for word in scope):
            out.append(line)
    return out


# 사실 키 → 그 자료가 없을 때 이유를 적어야 하는 절
_MISSING_SECTIONS = {
    "verdict": "verdict", "alternatives": "alternatives", "metrics_history": "reasons", "shocks": "reasons",
    "analogs": "analogs", "hour_gap": "conditions", "profile": "conditions", "commerce_change": "conditions",
    "funding_candidates": "funding",
}


def missing_data_gaps(facts: dict, sections: dict[str, str]) -> list[str]:
    """자료가 없는 자리(available false·표본 부족 신호)인데 해당 절에 그 이유가 그대로 적히지 않은 항목.

    이유를 적는 자리는 코드가 그 줄만 쓴다 — 추정 문장이 끼어들 틈이 없다(report_sections 단위 테스트가 고정).
    """
    gaps = [
        key for key, section in _MISSING_SECTIONS.items()
        if isinstance(value := facts.get(key), dict) and value.get("available") is False
        and (value.get("reason") or "") not in sections[section]
    ]
    signals = (facts.get("verdict") or {}).get("signals") or []
    return gaps + [
        f"signal:{s.get('key')}" for s in signals
        if s.get("level") == "unavailable" and (s.get("evidence") or "") not in sections["reasons"]
    ]
```

5. `# ── 판정자에게 보이는 본문의 모델명 가리기 ───` 머리 **바로 위**(기존 `judge_packets` 다음)에 넣는다:

```python
def answer_packets(
    scenario_id: str, question: str | None, body: str, answers: dict[str, str], seed: int,
) -> tuple[str, dict[str, str]]:
    """해석 판정 묶음 — 질문 + 코드가 쓴 본문 한 벌 + 모델명을 A·B…로 가린 해석들. 순서는 시드로 결정적."""
    models = sorted(answers)
    random.Random(f"{seed}:{scenario_id}").shuffle(models)
    mapping = {chr(ord("A") + i): model for i, model in enumerate(models)}
    parts = [f"# 시나리오 {scenario_id}", "", f"채점 기준: `{ANSWER_RUBRIC_PATH}`", "",
             f"질문: {question or '(없음 — 총평)'}", "",
             "## 리포트 본문 (코드가 사실로 쓴 6개 절 — 해석의 유일한 근거)", "", body]
    for blind, model in mapping.items():
        parts += ["", f"## 해석 {blind}", answers[model]]
    return "\n".join(parts) + "\n", mapping
```

- [ ] **Step 4: Implement — `benchmark_report.py`**

1. 모듈 docstring: `freeze` 사용 줄 다음에 `  python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check` 줄을 넣고, `150건 평가셋은 freeze·run·score에 ...` 문장을 아래로 바꾼다:

```text
150건 평가셋은 freeze·sections-check·run·score·judge-export에 `--scenario-set 150`을 붙인다(시나리오·facts 경로만 바뀐다).

v0.68.0(리포트 코드 우선 구조)부터 6개 절은 코드가 facts로 쓴다 — `sections-check`가 모델 호출 없이 범위 없는 숫자·
이유 빠진 자료 부족 자리를 센다. LLM은 맨 위 해석(answer) 한 단락만 쓰므로 `score`·`judge-export`는 그 단락만 본다.
```

2. import 정리 — 결과가 아래와 같아야 한다(바뀐 줄만):

```python
import argparse
import json
import random
import re
import subprocess
...
from dataclasses import dataclass
...
from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    SCOPE_WORDS,
    answer_packets,
    intent_gates,
    classify_violation,
    judge_packets,
    mask_model_names,
    missing_data_gaps,
    render_llm_report,
    report_gates,
    unscoped_number_lines,
)
```

지울 import: `replace`(dataclasses), `consistency`·`llm_sections`·`unmatched_numbers`·`verdict_matches`·`verdict_states_grade`(scoring), `FinanceFactsGateway`, `build_tools`, `GUARD_EVENTS`. interactor import는 한 줄로: `from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK, AnalysisInteractor`. 추가: `from apps.agent.domain.services.report_guards import contradicts_verdict`, `from apps.agent.domain.services.report_sections import build_sections`(report_sampling import 다음 줄).

3. `_JUDGE_SEED = 0` 다음에:

```python
_HUMAN_SAMPLE = 20  # 사람 검수 표본(설계서 §7) — judge-export가 시드로 고정해 human_sample.json에 남긴다
_DIGITS = re.compile(r"\d+")
```

4. `collect_run`부터 `guard_summary`까지(즉 `collect_run`·`_report_text`·`_written_sections`·`_tool_spec_text`·`score_run`·`score_record`·`guard_summary`)를 아래로 통째로 바꾼다:

```python
def collect_run(events: Iterable[AgentEvent], clock: Callable[[], float] = time.perf_counter) -> dict:
    """이벤트 스트림 → {first_ms, total_ms, sections}.

    시계는 facts 이벤트 수신을 0으로, 해석(answer) 단락까지(first_ms)·report_done까지(total_ms)를 잰다.
    6개 절은 사실 수집 직후 곧바로 나가므로 지연의 의미가 해석 기준으로 바뀌었다(v0.68.0).
    """
    start: float | None = None
    first_ms = total_ms = None
    sections: dict[str, str] = {}
    for event in events:
        if event.type == "facts":
            start = clock()
        elif event.type == "report_delta":
            section = event.payload["section"]
            if section == "answer" and first_ms is None and start is not None:
                first_ms = (clock() - start) * 1000
            sections[section] = sections.get(section, "") + event.payload["markdown"]
        elif event.type == "report_done" and start is not None:
            total_ms = (clock() - start) * 1000
    return {"first_ms": first_ms, "total_ms": total_ms, "sections": sections}


def _report_text(sections: dict[str, str]) -> str:
    return concat_sections(sections.items())


def score_run(record: dict, facts: dict) -> dict:
    """한 회차 채점 — 해석(answer) 한 단락만 본다. 6개 절은 코드라 결정적이다(sections-check·단위 테스트).

    `digits`는 가드 뒤에도 남은 숫자 토큰 수(0이어야 한다), `removed_sentences`·`raw_contradiction`은 시도 기록에서
    가드가 지운 문장 수와 판정 모순으로 실패한 시도가 있었는지다.
    """
    answer = record["sections"].get("answer", "")
    attempts = record.get("answer_attempts") or []
    return {
        "complete": not record.get("error") and bool(answer),
        "fallback": answer == ANSWER_FALLBACK,
        "verdict_ok": not contradicts_verdict(answer, facts.get("verdict")),
        "digits": len(_DIGITS.findall(answer)),
        "removed_sentences": sum(a.get("removed_sentences", 0) for a in attempts),
        "raw_contradiction": any(a.get("contradiction") for a in attempts),
        "rule_hits": check_rule_keywords(answer),
    }


def score_summary(model: str, runs: list[dict]) -> dict:
    """모델 요약 — evaluate 호환 키(completion·verdict_match·fabrication·…)와 해석 지표(`answer`).

    호환 키는 모두 해석 단락 기준이다: fabrication = 가드 뒤에도 숫자가 남은 해석 비율(0이어야 한다).
    """
    n = len(runs)
    return {
        "model": model, "n": n,
        "completion": sum(r["complete"] for r in runs) / n,
        "verdict_match": sum(r["verdict_ok"] for r in runs) / n,
        "fabrication": sum(r["digits"] > 0 for r in runs) / n,
        "rule_violations_keyword": sum(len(r["rule_hits"]) for r in runs),
        "first_p95_ms": _p95([r["first_ms"] for r in runs]),  # 해석 단락이 나온 시각(본문 6개 절은 즉시)
        "total_p95_ms": _p95([r["total_ms"] for r in runs]),
        "answer": {
            "fallback_rate": sum(r["fallback"] for r in runs) / n,
            "digits_after_guard": sum(r["digits"] for r in runs),
            "raw_contradiction_rate": sum(r["raw_contradiction"] for r in runs) / n,
            "removed_sentences": sum(r["removed_sentences"] for r in runs),
        },
        "sampling": sampling_label(runs),
        "runs": [{k: r[k] for k in ("id", "rep", "complete", "fallback", "verdict_ok", "digits", "removed_sentences",
                                    "raw_contradiction", "rule_hits", "first_ms", "total_ms", "error")} for r in runs],
    }
```

5. `run_record`를 바꾼다:

```python
def run_record(scenario_id: str, rep: int, got: dict, error: str | None, interactor) -> dict:
    """캐시 한 줄 — 화면 본문(`sections`, 해석 포함)과 해석 시도 기록(`answer_attempts`: 원문·지운 문장 수·모순·오류)."""
    usage = interactor.last_usage
    return {"id": scenario_id, "rep": rep, **got, "answer_attempts": interactor.last_answer_attempts,
            "error": error, "temperature": REPORT_TEMPERATURE, "seed": REPORT_SEED,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}}
```

6. `_cmd_freeze` 바로 위에 새 명령을 넣는다:

```python
def _cmd_sections_check(args: argparse.Namespace) -> None:
    """코드 절 자동 검사(설계서 §7) — 세트 전체 facts로 6개 절을 써서 범위 없는 숫자 줄·이유 빠진 자료 부족 자리를 센다.

    모델을 부르지 않는다. 결과는 `sections_check.json`(문제 있는 시나리오만 줄 단위로)이다.
    """
    scenarios = _scenarios()
    issues: dict[str, dict] = {}
    for s in scenarios:
        facts = _facts_of(s["id"])
        sections = build_sections(facts)
        region = facts.get("region") or {}
        regions = (facts.get("alternatives") or {}).get("regions") or []
        # 동 이름에 숫자가 든다("상계3.4동") — 이름은 숫자로 세지 않는다
        names = [n for n in (region.get("name"), *(r.get("region_name") for r in regions)) if n]
        scope = [w for w in (region.get("name"), region.get("industry_name"), *SCOPE_WORDS) if w]
        found = {
            "unscoped": [line for md in sections.values() for line in unscoped_number_lines(md, scope, names)],
            "missing": missing_data_gaps(facts, sections),
        }
        if any(found.values()):
            issues[s["id"]] = found
    _write_json(_RUNS / "sections_check.json", {"scenarios": len(scenarios), "issues": issues})
    print(f"sections-check: {len(scenarios)}건 중 문제 {len(issues)}건 → {_RUNS / 'sections_check.json'}", flush=True)
```

7. `_recording` 함수를 지운다. `_cmd_run`의 도구 배선을 지우고 인터랙터 생성·출력 없음 판정·기록 줄을 바꾼다 — 결과:

```python
def _cmd_run(args: argparse.Namespace) -> None:
    model = REPORT_MODELS[args.model]
    llm = model.llm()
    if model.local:
        _load(model.name, options=_LOCAL_OPTIONS)  # 워밍업 — 모델 로드 시간은 지연에서 제외
    path = _run_path(model.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["id"], r["rep"]) for r in _read_jsonl(path)}
    for rep in range(args.repeat):
        for s in _scenarios():
            if (s["id"], rep) in done:
                continue
            frozen = FrozenFacts({(s["region_code"], s["industry_id"]): _facts_of(s["id"])})
            interactor = AnalysisInteractor(llm=llm, facts=frozen)  # 모델 하나만 평가한다 — 재시도 모델 없음
            error = None
            events: list[AgentEvent] = []

            def stream():
                for event in interactor.run(s["region_code"], s["industry_id"], s["question"]):
                    events.append(event)
                    yield event

            try:
                got = collect_run(stream())
            except Exception as exc:  # 모델·전송 실패도 한 회차의 결과다 — 완주 게이트가 걸러낸다
                error = f"{type(exc).__name__}: {exc}"
                got = {**collect_run(events), "first_ms": None, "total_ms": None}  # 중단된 회차의 시간은 의미 없다
            if not error and interactor.last_usage.output_tokens == 0:
                error = "no_llm_output"
                print(f"run: 경고 {model.name} {s['id']} rep{rep} LLM 출력 없음", flush=True)
            row = run_record(s["id"], rep, got, error, interactor)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"run: {model.name} {s['id']} rep{rep} total={got['total_ms']} error={error}", flush=True)
```

8. `_cmd_score`를 바꾼다:

```python
def _cmd_score(args: argparse.Namespace) -> None:
    facts = {s["id"]: _facts_of(s["id"]) for s in _scenarios()}
    for name in REPORT_MODELS:
        records = _read_jsonl(_run_path(name))
        if not records:
            continue
        runs = [{**r, **score_run(r, facts[r["id"]])} for r in records]
        _write_json(_score_path(name), score_summary(name, runs))
        print(f"score: {name} → {_score_path(name)}", flush=True)
```

9. `_first_rep_reports`를 `_first_rep_answers`로 바꾸고, `_cmd_judge_export`의 비교 모드 아닌 경로를 바꾼다:

```python
def _first_rep_answers() -> dict[str, tuple[str, dict[str, str]]]:
    """{시나리오 id: (코드 6개 절 본문, {모델: 1회차 해석})} — 해석의 모델명은 가린다. 본문은 모델과 무관하게 같다."""
    out: dict[str, tuple[str, dict[str, str]]] = {}
    for name in REPORT_MODELS:
        for r in _read_jsonl(_run_path(name)):
            answer = r["sections"].get("answer")
            if r["rep"] == 0 and answer:
                body = concat_sections((k, v) for k, v in r["sections"].items() if k != "answer")
                out.setdefault(r["id"], (body, {}))[1][name] = mask_model_names(answer)
    return out
```

```python
def _cmd_judge_export(args: argparse.Namespace) -> None:
    if args.compare_tag:
        _export_compare(args)
        return
    _JUDGE.mkdir(parents=True, exist_ok=True)
    questions = {s["id"]: s["question"] for s in _scenarios()}
    mapping: dict[str, dict[str, str]] = {}
    for sid, (body, answers) in _first_rep_answers().items():
        packet, mapping[sid] = answer_packets(sid, questions.get(sid), body, answers, _JUDGE_SEED)
        (_JUDGE / f"packet_{sid}.md").write_text(packet, encoding="utf-8")
    _write_json(_JUDGE / "mapping.json", mapping)
    # 사람 검수 표본 — 같은 시드면 같은 20건
    sample = sorted(random.Random(_JUDGE_SEED).sample(sorted(mapping), min(_HUMAN_SAMPLE, len(mapping))))
    _write_json(_JUDGE / "human_sample.json", sample)
    print(f"judge-export: {len(mapping)}개 시나리오(사람 검수 {len(sample)}건) → {_JUDGE}", flush=True)
```

10. `_COMMANDS`에 `"sections-check": _cmd_sections_check`를 `"freeze"` 다음에 넣는다:

```python
    "freeze": _cmd_freeze, "sections-check": _cmd_sections_check, "run": _cmd_run, "score": _cmd_score, "judge-export": _cmd_judge_export,
```

- [ ] **Step 5: 해석 판정 기준 파일**

`data/eval/report_answer_rubric.md`:

```markdown
# 해석 단락 판정 기준 (리포트 코드 우선 구조, 2026-10-05)

리포트 본문 6개 절은 코드가 사실 묶음에서 쓴 결정적 글이다 — 판정 대상이 아니다. 판정 대상은 맨 위 **해석** 한 단락(3~5문장)뿐이다.
같은 시나리오의 해석이 A, B… 로 이름이 가려져 있다. 어느 모델인지 추측하지 않는다. 본문의 "[모델]"은 가려진 이름이다.

읽을 것:
1. 판정 묶음 `.../packet_<id>.md` — 질문 + 리포트 본문 6개 절 + 해석들. **본문이 해석의 유일한 근거다.**
2. 필요할 때만 사실 묶음 원본 `data/eval/report_facts_150/<id>.json`.

해석마다 매길 것:
- `answered` (true/false): 질문이 있으면 질문에 직접 답했는가. 질문이 없으면 "이 동네에서 이 업종을 한다면 먼저 볼 것"을 짚었는가.
- `core_error` (true/false): 본문과 어긋난 말이 하나라도 있는가 — 판정 등급을 바꿔 말함, 본문에 없는 사실을 보탬, 본문이 "자료 부족"이라 한 곳을 추정으로 메움, 시간대·대안 등급·지원사업을 본문과 다르게 옮김, 응답 규칙 위반(① 외국인 비하·차별 ② 2020~2022년 폐업률 왜곡 가능성 무시 ③ 대출 중개·특정 은행·상품 추천).
- `errors` (목록): `core_error`가 true면 어긋난 문장과 이유를 한 줄씩. 없으면 [].
- `hard_to_judge` (true/false): 본문만으로 맞는지 판단하기 어려웠는가(무엇의 수치·말인지 모호 등). 이유는 `note`에.
- `note`: 한 줄 근거.

코드 폴백 문장("질문에 대한 해석을 만들지 못했습니다. 아래 사실을 직접 확인해 주세요.")은 `answered: false`, `core_error: false`로 매긴다.

출력: 판정 폴더(`data/eval/cache/llm-benchmark/judge-<태그>/`)에 `verdict_<id>.json` — 아래 형식 JSON 하나:
{"<id>": {"A": {"answered": true, "core_error": false, "errors": [], "hard_to_judge": false, "note": "한 줄 근거"}, "B": {...}}}
묶음에 있는 모든 해석 이름(A, B, …)을 빠짐없이. python3로 파싱되는지 확인한다. 다른 파일은 건드리지 않는다. 서브에이전트를 띄우지 않는다.
회신은 "verdict_<id>.json 작성, 해석 N개, 핵심 오류 k건, 판단 어려움 h건" 한 줄.

사람 검수(20건, `human_sample.json`)도 같은 기준이다 — 해석 단락만 본다.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/ -q`
Expected: 전부 PASS (bench CLI 포함 — Task 3의 `--ignore`가 더는 필요 없다).

- [ ] **Step 7: 코드 절 자동 검사를 실제 facts로 한 번 돌린다 (모델 호출 없음)**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check --scenario-set 150 --cache-tag codefirst150 && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check`
Expected: `sections-check: 150건 중 문제 0건 → …/report-codefirst150/sections_check.json`, `sections-check: 12건 중 문제 0건 → …`. 문제가 나오면 `sections_check.json`의 줄을 보고 Task 1의 해당 작성 함수에 범위(동·업종 이름 또는 "서울")나 이유를 보태고 Task 1 테스트를 다시 돌린 뒤 이 단계를 반복한다(설계서 §9 "문장 다듬기는 실데이터 150건 출력을 보고 한 번 조정").

- [ ] **Step 8: 버전 로그**

`## [v0.68.0]`의 `### Added`에 두 줄, `### Changed`에 한 줄:

```markdown
- 리포트 벤치 `sections-check` 명령 — 모델 호출 없이 세트 전체 facts로 6개 절을 써서 "범위 없는 숫자 줄"(숫자 토큰이 있는데 동·업종 이름·서울·전국·동 전체·업종 무관·최근이 없는 줄, 공고 제목 「」·숫자 든 동 이름 제외)과 "이유 빠진 자료 부족 자리"(available false·표본 부족 신호인데 해당 절에 이유가 없음)를 센다. 150건·12건 모두 0건.
- 해석 판정 기준 `data/eval/report_answer_rubric.md`와 `judge-export`의 해석 묶음(질문 + 코드 본문 한 벌 + 가린 해석, `human_sample.json` 사람 검수 20건 시드 고정).
```

```markdown
- 리포트 벤치 채점이 해석(answer) 단락만 본다 — 완주(해석 있음·오류 없음)·폴백 비율·가드 뒤 숫자 수·판정 모순(가드 뒤)·가드 전 모순 시도 비율·지운 문장 수·규칙 키워드. 첫 글자 지연(`first_ms`)은 해석 단락이 나온 시각이다(6개 절은 사실 수집 직후 즉시라 의미가 바뀜). 회차 기록은 `answer_attempts`(모델별 원문·지운 문장 수·모순·오류)를 남기고 도구 결과·가드 전 절 원문은 남기지 않는다. 벤치는 모델 하나만 평가한다(재시도 모델 없음).
```

- [ ] **Step 9: Commit**

```bash
git add backend/apps/agent/adapter/inbound/cli/benchmark_report.py backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py backend/tests/test_report_bench_cli.py backend/tests/test_report_bench_scoring.py data/eval/report_answer_rubric.md backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 벤치 — 해석 단락 채점·코드 절 자동 검사·해석 판정 묶음

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 새 구조에서 쓰지 않는 리포트 코드 정리

**Files:**
- Replace: `backend/apps/agent/app/use_cases/agent_tools.py` (`hit_to_dict`만)
- Delete: `backend/tests/test_agent_tools.py`, `backend/apps/agent/domain/services/report_fallback.py`, `backend/tests/test_agent_report_fallback.py`, `backend/apps/agent/adapter/outbound/gateways/finance_facts_gateway.py`
- Modify: `backend/apps/agent/app/ports/output/agent_port.py` (`RegionFactsPort.latest_rates`, `FinanceFactsPort` 삭제)
- Modify: `backend/apps/agent/adapter/outbound/gateways/region_facts_gateway.py` (`latest_rates`, `InterestRateOrm` import 삭제)
- Modify: `backend/tests/test_agent_report_facts.py` (대역의 `latest_rates` 삭제)
- Modify: `backend/tests/test_report_sampling.py` (`build_tools` import·`test_대출_금리_도구_설명에_예시값이_없다` 삭제)
- Replace: `backend/apps/agent/domain/services/section_stream.py` (`SECTION_ORDER`·`concat_sections`만)
- Modify: `backend/tests/test_agent_section_stream.py` (분할기 테스트 삭제)
- Modify: `backend/apps/agent/domain/services/report_guards.py` (스트리밍 절 가드 삭제, docstring)
- Modify: `backend/tests/test_report_guards.py` (삭제된 이름의 테스트 25개 삭제·1개 수정)
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 3·4 이후 아무도 import하지 않는 이름들 — 지우기 전 `grep -rn "<이름>" backend/apps backend/tests`로 0건임을 확인한다.
- Produces: 남는 공개 이름 — `agent_tools.hit_to_dict`, `section_stream.SECTION_ORDER`/`concat_sections`, `report_guards`의 `VERDICT_SYNONYMS`·`verdict_matches`·`verdict_states_grade`·`GRADE_LABELS`·`EMPHASIS_ONLY_LABELS`·`verdict_contradiction`·`stated_grades`·`contradicts_verdict`·`strip_links`·`UrlStripper`·`FUNDING_DISCLAIMER`·`drop_digit_sentences`·`GuardedAnswer`·`guard_answer`.

- [ ] **Step 1: 지울 이름이 쓰이지 않는지 확인**

Run: `cd backend && grep -rn "build_tools\|AgentTool\|compare_rent_vs_buy\|FinanceFacts\|latest_rates\|report_fallback\|SectionSplitter\|LeadingTagGuard\|ensure_leading_tag\|disclaimer_suffix\|GUARD_EVENTS\|ReportGuard\|guard_section" apps tests | grep -v "^apps/agent/app/use_cases/agent_tools.py\|^apps/agent/domain/services/report_fallback.py\|^apps/agent/domain/services/section_stream.py\|^apps/agent/domain/services/report_guards.py\|^apps/agent/adapter/outbound/gateways/finance_facts_gateway.py\|^apps/agent/app/ports/output/agent_port.py\|^apps/agent/adapter/outbound/gateways/region_facts_gateway.py\|^tests/test_agent_tools.py\|^tests/test_agent_report_fallback.py\|^tests/test_agent_section_stream.py\|^tests/test_report_guards.py\|^tests/test_report_sampling.py\|^tests/test_agent_report_facts.py"`
Expected: 출력 없음 (`apps/funding/...LatestRatesGateway`는 다른 BC의 다른 이름 — grep 패턴 `latest_rates`가 `latest_rates_gateway`에 걸리면 그 줄은 무시한다).

- [ ] **Step 2: 도구 정의·폴백·finance 게이트웨이 삭제**

`backend/apps/agent/app/use_cases/agent_tools.py`를 통째로 바꾼다:

```python
"""RAG 검색 결과 → facts 직렬화 (`facts.news`가 쓴다).

v0.68.0(리포트 코드 우선 구조)에서 리포트 도구 루프를 걷어냈다 — 평가 252회에서 도구 호출 0회였고,
자금 계획은 별도 화면이다. 남은 것은 facts 수집이 쓰는 변환 하나다.
"""

from apps.rag.domain.entities.rag_chunk_entity import RagHit


def hit_to_dict(hit: RagHit) -> dict:
    return {
        "chunk_id": hit.chunk_id,
        "source_type": hit.source_type,
        "source_id": hit.source_id,
        "content": hit.content,
        "score": hit.score,
        "url": hit.url,
        "org": hit.org,
        "published_at": hit.published_at.isoformat() if hit.published_at else None,
    }
```

```bash
git rm backend/tests/test_agent_tools.py backend/apps/agent/domain/services/report_fallback.py backend/tests/test_agent_report_fallback.py backend/apps/agent/adapter/outbound/gateways/finance_facts_gateway.py
```

`backend/apps/agent/app/ports/output/agent_port.py`: `RegionFactsPort`의 `latest_rates` 추상 메서드 4줄(`@abstractmethod` ~ docstring + 빈 줄)을 지우고, 파일 끝의 `class FinanceFactsPort(ABC):` 전체와 그 앞 빈 줄 두 줄을 지운다(파일은 `EventAnalogFactsPort.analogs` docstring 다음 개행 하나로 끝난다).

`backend/apps/agent/adapter/outbound/gateways/region_facts_gateway.py`: `def latest_rates(self) -> dict:` 메서드 전체(9줄 + 뒤 빈 줄)와 `from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm` import를 지운다.

`backend/tests/test_agent_report_facts.py`: 대역 클래스의 아래 3줄을 지운다:

```python
    def latest_rates(self) -> dict:
        return {"loan_facility": 4.05}

```

`backend/tests/test_report_sampling.py`: `from apps.agent.app.use_cases.agent_tools import build_tools` 줄과 마지막 테스트 `test_대출_금리_도구_설명에_예시값이_없다` 전체를 지운다(파일은 `test_운영_점검_프로브도_리포트와_같은_샘플링을_쓴다`로 끝난다).

- [ ] **Step 3: `section_stream.py` 축소**

`backend/apps/agent/domain/services/section_stream.py`를 통째로 바꾼다:

```python
"""리포트 절 조각 → 저장용 마크다운 (stdlib만 import).

SSE `report_delta`는 절 이름과 마크다운 조각이다. 저장본(analysis_report.report_md)·벤치·평가 러너는 이 모듈로
절별로 이어 붙이고 계약 순서로 정렬한다.
"""

from collections.abc import Iterable

# 저장·표시 기준 섹션 순서 — 맨 위 해석(answer) 다음에 코드 6개 절(report_sections.SECTION_TITLES 순서).
# 해석은 6개 절보다 늦게 도착하지만 저장본은 화면처럼 맨 위다. answer 없는 옛 저장본은 그대로다.
SECTION_ORDER = ("answer", "verdict", "reasons", "analogs", "conditions", "alternatives", "funding")


def concat_sections(
    chunks: Iterable[tuple[str, str]], order: Iterable[str] = SECTION_ORDER
) -> str:
    """조각 목록 → 저장용 마크다운. 섹션 안은 그대로 잇고, 섹션끼리는 빈 줄로 나눈다.

    섹션은 `order` 순서로 정렬한다 — 도착 순서가 뒤섞여도(폴백이 뒤늦게 붙는 경우) 저장본은
    늘 계약 순서다. `order`에 없는 섹션은 뒤에 도착 순서대로 남긴다(버리지 않는다).
    """
    ranking = list(order)
    sections: dict[str, list[str]] = {}
    for section, chunk in chunks:
        sections.setdefault(section, []).append(chunk)
    names = sorted(
        sections, key=lambda name: ranking.index(name) if name in ranking else len(ranking)
    )
    return "\n\n".join("".join(sections[name]) for name in names)
```

`backend/tests/test_agent_section_stream.py`: 모듈 docstring·import를 아래로 바꾸고, `_feed_all` 헬퍼와 `SectionSplitter`를 쓰는 테스트 10개(`test_마커가_조각_경계에_걸쳐도_섹션을_알아본다` ~ `test_붙들고_있던_꼬리는_flush가_한_번만_낸다`)를 지운다. `concat_sections` 테스트 3개와 순서 상수 테스트는 남긴다.

```python
"""section_stream — 리포트 절 조각을 저장용 마크다운으로 잇는다 (계약 순서 정렬)."""

from apps.agent.domain.services.section_stream import SECTION_ORDER, concat_sections
```

- [ ] **Step 4: `report_guards.py` 스트리밍 절 가드 삭제**

1. 모듈 docstring을 아래로 바꾼다:

```python
"""리포트 출력 코드 가드 — LLM 글이 화면에 나가기 전에 코드가 지키는 선 (stdlib만 import).

v0.68.0(리포트 코드 우선 구조)부터 LLM은 맨 위 해석(answer) 한 단락만 쓴다. 6개 절은 코드가 facts로 쓰므로
가드는 해석 단락에만 건다(`guard_answer`).

- **판정 모순**: facts와 다른 등급을 단정하면 그 단락은 실패 — 다음 모델로 넘긴다(`verdict_contradiction`).
- **링크·공고 번호 제거**: URL·bizinfo 공고 번호를 지운다(`UrlStripper`·`strip_links`).
- **숫자 문장 삭제**: 숫자가 든 문장을 지운다(`drop_digit_sentences`) — 숫자는 본문이 범위와 함께 보여 준다.
- 판정 등급 동의어·대조 규칙은 벤치 채점과 같은 단일 원천이다. 지원사업 절의 예상치 고지문(`FUNDING_DISCLAIMER`)도 여기 둔다.
"""
```

2. `from collections.abc import Callable` import를 지운다.
3. `# ── 기본 신뢰 태그 ───` 머리부터 `def guard_section(...)` 끝까지(`_TRUST_TAGS`·`DEFAULT_TAG`·`_BLOCK_START`·`_MAYBE_BLOCK`·`_HEADING_SLACK`·`LeadingTagGuard`·`ensure_leading_tag`·`# ── 예상치 고지문` 블록·`disclaimer_suffix`·`# ── 절별 가드 조립` 블록·`GUARD_EVENTS`·`_PlainGuard`·`_TaggedGuard`·`_FundingGuard`·`_VerdictGuard`·`ReportGuard`·`_pair`·`guard_section`)를 지우고 그 자리에 아래만 남긴다(바로 뒤가 Task 2의 `# ── 해석(answer) 단락 가드` 블록):

```python
# ── 예상치 고지문 ────────────────────────────────────────────────

FUNDING_DISCLAIMER = "[확인된 사실] 금리·한도는 예상치이며, 신청 자격·한도는 공고 원문에서 확인해야 합니다."


```

`backend/tests/test_report_guards.py`:

1. import를 아래로 바꾼다:

```python
from apps.agent.domain.services.report_guards import (
    UrlStripper,
    contradicts_verdict,
    drop_digit_sentences,
    guard_answer,
    strip_links,
    verdict_contradiction,
)
```

2. 헬퍼 `_run`·`_joined`·`_tagged`·`_titled`와 아래 테스트 25개를 지운다: `test_태그가_없으면_본문_앞에_확인된_사실을_붙인다`, `test_LLM이_붙인_태그는_그대로_둔다`, `test_헤딩_뒤_공백이_조각으로_갈려도_본문_첫_글자에서_판단한다`, `test_헤딩이_없으면_첫_글자부터_본문이다`, `test_본문이_없으면_태그를_붙이지_않는다`, `test_고지문이_없으면_덧붙이고_있으면_중복하지_않는다`, `test_모순된_판정_절은_폴백으로_교체된다`, `test_판정_절은_절이_끝날_때_한_번에_나간다`, `test_다시_열린_판정_절이_모순이면_버린다`, `test_지원사업_절이_끝나면_고지문을_덧붙인다`, `test_유사_사례_절은_태그를_붙이지_않는다`, `test_모든_절에서_링크를_지운다`, `test_한_절_통째로_가드를_씌운다`, `test_맨_제목_줄_다음_줄에_태그를_붙인다`, `test_굵은_제목과_콜론_제목도_제목으로_본다`, `test_제목_뒤_콜론에_이어_쓴_본문은_콜론_뒤에_태그를_붙인다`, `test_제목으로_시작하는_문장은_제목이_아니다`, `test_제목이_조각으로_갈려도_인식한다`, `test_제목이_아닌_본문은_줄_끝을_기다리지_않는다`, `test_목록으로_시작하는_본문은_태그를_따로_한_문단으로_둔다`, `test_숫자나_굵은_글씨로_시작하는_문장은_목록이_아니다`, `test_굵은_태그도_이미_붙은_태그로_본다`, `test_링크를_지워_판정_절이_비면_폴백을_낸다`, `test_가드가_개입_횟수와_교체_이유를_남긴다`, `test_소제목이나_코드_블록으로_시작하는_본문은_태그를_따로_한_문단으로_둔다`.
3. `test_긴_공백도_선형_시간에_처리한다`의 끝 세 줄을 아래 두 줄로 바꾼다(`guard_section`이 사라진다 — 링크 제거의 선형 시간만 본다):

```python
    assert time.perf_counter() - started < 0.5
    assert whole == streamed and whole.endswith("뒤 끝")
```

- [ ] **Step 5: Run the full suite**

Run: `cd backend && /home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python -m pytest tests/ -q`
Expected: 전부 PASS (약 1,200건 — 계획 검증 시 1206 passed). 그리고 Step 1의 grep을 다시 돌려(이번엔 제외 목록 없이) `apps/funding` 줄 말고는 출력이 없어야 한다.

- [ ] **Step 6: 버전 로그**

`## [v0.68.0]`의 `### Removed`에 한 줄:

```markdown
- 새 구조에서 쓰지 않는 리포트 코드 정리 — 리포트 도구 정의(`build_tools`·`AgentTool`·`compare_rent_vs_buy`, `agent_tools.py`에는 `hit_to_dict`만), finance 엔진 게이트웨이(`FinanceFactsGateway`·`FinanceFactsPort`)와 `RegionFactsPort.latest_rates`, LLM 절 폴백 포매터 `report_fallback.py`(정식 본문은 `report_sections.py`), 마커 분할기 `SectionSplitter`, 스트리밍 절 가드(`ReportGuard`·`LeadingTagGuard`·`disclaimer_suffix`·`guard_section`·`GUARD_EVENTS`)와 각 테스트. 판정 동의어·모순 검사·링크 제거·예상치 고지문은 남는다.
```

- [ ] **Step 7: Commit**

```bash
git add -A backend/apps/agent backend/tests backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 새 구조에서 쓰지 않는 도구·폴백·분할기·절 가드 정리

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: 프론트엔드 — `answer` 섹션 계약과 "해석" 블록 (Codex 위임)

**컨트롤러가 위임한다:** 아래 브리프를 그대로 `codex exec`에 넘긴다(구현은 Codex, 검수는 컨트롤러).
워크트리 `frontend/`에는 `node_modules`가 없다 — 먼저 메인 저장소 것을 링크한다(`frontend/.gitignore`가 `/node_modules`를 무시한다):

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first/frontend
[ -e node_modules ] || ln -s /home/kimchungsik/projects/cloud.beyondfacade/frontend/node_modules node_modules
codex exec --cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first/frontend "$(cat <<'BRIEF'
작업: 창업 경고 리포트 SSE 계약에 맨 위 해석(answer) 섹션을 추가하고, 리포트 화면 맨 위에 "해석" 블록을 그린다.
먼저 frontend/AGENTS.md와 CLAUDE.md(Part V 프론트 규칙)를 읽고 따른다. 이 브리프에 적힌 파일만 바꾼다. 커밋하지 않는다.

배경(백엔드 v0.68.0, 이미 구현됨): 리포트 6개 절(verdict·reasons·analogs·conditions·alternatives·funding)은 이제
코드가 사실로 쓰고, LLM은 맨 위 해석 한 단락만 쓴다. SSE는 6개 절 report_delta(절당 한 조각)가 먼저 오고, 그 뒤에
report_delta {section: "answer", markdown} 가 한 번 온 다음 report_done. answer에는 숫자가 없다(3~5문장 한 단락).
answer가 없는 리포트(옛 저장본·작성 중)는 해석 블록을 그리지 않는다. 6개 절의 그림·차트·본문 렌더는 그대로다.

바꿀 것:
1. src/shared/api/types.ts
   - ReportSection에 "answer"를 맨 앞에 추가:
     export type ReportSection = "answer" | "verdict" | "reasons" | "analogs" | "conditions" | "alternatives" | "funding";
   - 바로 아래에 추가:
     /** 코드가 사실로 쓰는 6개 절 — 맨 위 해석(answer)을 뺀 나머지. 그림·제목은 이 절들에만 있다. */
     export type FactSection = Exclude<ReportSection, "answer">;
2. src/features/agent-report/components/report-visuals.tsx
   - ReportSection 대신 FactSection을 쓴다(import, VISUALS의 `satisfies Record<FactSection, …>`, ReportVisuals의 section prop 타입).
3. src/features/agent-report/components/report-view.tsx
   - SECTION_ORDER: FactSection[], SECTION_LABEL: Record<FactSection, string>, SECTION_FORMAT: Partial<Record<FactSection, …>>,
     sectionBody(state, section: FactSection). import는 `import type { FactSection, ReportFacts } from "@/shared/api/types";`.
   - `<div className={styles.reportBody}>` 안, 6개 절 map보다 앞에 state.sections.answer가 있을 때만 해석 블록을 그린다:
     <section aria-label="해석"> + 제목(h2) "해석" + 안내 한 줄 "AI가 아래 사실을 읽고 쓴 해석입니다. 판정과 수치는 아래 사실을 기준으로 보세요."
     + 본문은 기존 절과 같은 ReactMarkdown(REMARK_PLUGINS, `${styles.markdown} report-markdown`). 그림(ReportVisuals)·번호(01 / ANALYSIS)는 없다.
     스타일은 기존 reportSection 클래스와 토큰(var(--…))만 쓴다 — 하드코딩 hex 금지. 사실과 구분되는 라벨이면 된다(과한 장식 금지).
   - 빈 리포트 아웃라인(SECTION_ORDER 6개)과 절 번호는 그대로 6개 절 기준이다.
4. src/app/api/mock/fixtures.ts (agentEventScript)
   - 6개 절 report_delta를 push하는 for 루프 바로 뒤, writer done 앞에 해석 한 조각을 넣는다(숫자 금지):
     // 해석(answer)은 코드 6개 절 뒤에 한 번 — 숫자를 쓰지 않는 한 단락(실 API 계약과 같다)
     events.push({
       type: "report_delta", section: "answer",
       markdown: "판정 근거는 아래 신호와 폐업 추이에 있습니다. 손님이 몰리는 시간대에 맞춰 운영할 수 있는지 먼저 확인하세요. 같은 동네의 다른 업종과 같은 업종의 다른 동네도 함께 비교해 보세요.",
     });
5. 테스트 (먼저 쓰고 실패를 확인한 뒤 구현 — TDD)
   a. src/features/agent-report/components/report-view.test.tsx
      - import를 `import { render, screen, within } from "@testing-library/react";` 로 바꾸고 파일 끝에 추가:

it("해석이 오면 여섯 사실 절보다 위에 '해석' 블록으로 그린다", () => {
  let state = applyAgentEvent(initialAgentState(), { type: "report_delta", section: "verdict", markdown: "### 판정\n\n판정 본문" });
  state = applyAgentEvent(state, { type: "report_delta", section: "answer", markdown: "먼저 시간대를 확인하세요." });
  render(<ReportView state={state} />);
  const labels = screen.getAllByRole("region").map((region) => region.getAttribute("aria-label"));
  expect(labels.indexOf("해석")).toBeLessThan(labels.indexOf("판정"));
  expect(within(screen.getByRole("region", { name: "해석" })).getByText("먼저 시간대를 확인하세요.")).toBeInTheDocument();
});

it("해석이 없는 옛 리포트는 해석 블록 없이 여섯 절을 그대로 그린다", () => {
  let state = initialAgentState();
  for (const [section, title] of SECTIONS) {
    state = applyAgentEvent(state, { type: "report_delta", section, markdown: `### ${title}\n\n본문` });
  }
  render(<ReportView state={state} />);
  expect(screen.queryByRole("region", { name: "해석" })).not.toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(SECTIONS.map(([, title]) => title));
});

   b. src/app/api/mock/analysis/[id]/events/route.test.ts
      - 기존 테스트 "SSE 문장 조각은 같은 섹션에 반복되고 이어 붙이면 여섯 제목과 본문이 완성된다"의 섹션 순서 단언을 해석까지 포함하도록 바꾼다:
        expect([...new Set(deltas.map((e) => e.section))]).toEqual([...sections.map(([section]) => section), "answer"]);
      - 파일 끝에 계약 테스트 추가:

it("SSE 해석은 여섯 사실 절 뒤에 한 번 오고 숫자를 담지 않는다", async () => {
  const events = await readEvents();
  const deltas = events.filter((e): e is Extract<AgentEvent, { type: "report_delta" }> => e.type === "report_delta");
  const answers = deltas.filter((e) => e.section === "answer");
  expect(answers).toHaveLength(1);
  expect(deltas.at(-1)).toEqual(answers[0]);
  expect(new Set(deltas.slice(0, -1).map((e) => e.section))).toEqual(
    new Set(["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"]),
  );
  expect(answers[0].markdown).not.toMatch(/\d/);
});

   c. src/features/agent-report/lib/graded-paragraphs.ts 와 그 테스트는 바꾸지 않는다 — 통과만 확인한다.
6. frontend/docs/frontend_ver_log.md 맨 위(기존 ## [v0.52.1] 위, 머리 주석 아래)에:

## [v0.53.0] - 2026-10-05

### Added
- 리포트 맨 위 **해석** 블록 — SSE `report_delta {section: "answer"}`(백엔드 v0.68.0: 6개 절은 코드가 사실로 쓰고 LLM은 해석 한 단락만 쓴다)를 6개 사실 절 위에 "해석" 라벨과 안내 한 줄로 그린다. 그림·절 번호는 없다. answer가 없는 리포트(옛 저장본·작성 중)는 블록을 그리지 않는다.

### Changed
- `ReportSection`에 `"answer"` 추가, 6개 사실 절만 가리키는 `FactSection` 타입(`report-view`·`report-visuals`가 사용). mock SSE가 6개 절 뒤에 숫자 없는 해석 한 조각을 보낸다(계약 테스트로 고정).

완료 기준(이 셋이 모두 통과해야 한다):
- npx vitest run
- npx next typegen && npx tsc --noEmit
- git diff --stat 에 위 파일(types.ts, report-view.tsx, report-view.test.tsx, report-visuals.tsx, fixtures.ts, route.test.ts, frontend_ver_log.md)만 있다.
BRIEF
)"
```

**Files (Codex가 바꾼다):**
- Modify: `frontend/src/shared/api/types.ts`
- Modify: `frontend/src/features/agent-report/components/report-view.tsx`, `report-view.test.tsx`
- Modify: `frontend/src/features/agent-report/components/report-visuals.tsx`
- Modify: `frontend/src/app/api/mock/fixtures.ts`, `frontend/src/app/api/mock/analysis/[id]/events/route.test.ts`
- Modify: `frontend/docs/frontend_ver_log.md`

**Interfaces:**
- Consumes: 백엔드 SSE 계약(Task 3) — `report_delta {section: "answer", markdown}`가 6개 절 뒤에 한 번.
- Produces: `ReportSection`에 `"answer"`, `FactSection = Exclude<ReportSection, "answer">`.

- [ ] **Step 1: 위임 실행** — 위 `codex exec` 명령.
- [ ] **Step 2: 컨트롤러 검수** — 워크트리 `frontend/`에서:
  - `npx vitest run` → 전부 PASS (계획 검증 시 676 passed)
  - `npx next typegen && npx tsc --noEmit` → 오류 없음
  - `git diff --stat` — 브리프의 파일만 바뀌었는지, 하드코딩 hex·feature 간 import가 없는지 확인
  - `frontend/docs/frontend_ver_log.md` 맨 위가 `## [v0.53.0] - 2026-10-05`인지 확인(다른 브랜치와 번호 충돌 주의)
- [ ] **Step 3: Commit** (Codex가 커밋하지 않았다면)

```bash
git add frontend/src/shared/api/types.ts frontend/src/features/agent-report/components frontend/src/app/api/mock frontend/docs/frontend_ver_log.md
git commit -m "$(cat <<'EOF'
frontend v0.53.0: 리포트 맨 위 해석(answer) 블록과 SSE 계약

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: 150건 재평가와 결과 노트 (컨트롤러 직접 실행 — 모델 호출)

> 이 태스크는 서브에이전트에 넘기지 않는다. Gemini API·로컬 Ollama(gemma4:12b)를 부르고, 판정은 Claude 판정자(서브에이전트)와 사람 검수가 한다. 오래 걸리는 명령은 백그라운드로 돌리고 단계마다 사용자에게 한 줄 보고한다.

**Files:**
- Create: `data/eval/results/report-code-first-2026-10-05/notes.md`
- Create(복사): `data/eval/results/report-code-first-2026-10-05/{score_gemini-2.5-flash.json,score_gemma4_12b.json,sections_check.json,judge_scores.json,human_sample.json}`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 4 CLI(`sections-check`·`run`·`score`·`judge-export`·`judge-import`), `data/eval/report_answer_rubric.md`; 기준선 수치(설계서 §1·§7): 150건 리포트 전체 핵심 오류율 Claude 판정 Gemini 26.7%(95% 구간 19.8~34.5%)·gemma4:12b 80%.

- [ ] **Step 1: 사전 점검**

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first/backend
PY=/home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python
BR="-m apps.agent.adapter.inbound.cli.benchmark_report"
$PY $BR sections-check --scenario-set 150 --cache-tag codefirst150
```
Expected: `150건 중 문제 0건`. Gemini 키(`backend/.env` 심볼릭 링크)와 Ollama의 `gemma4:12b`가 있어야 한다(`curl -s http://localhost:11434/api/tags | grep gemma4:12b`).

- [ ] **Step 2: 두 모델 각 1회 실행** (백그라운드, gemma4:12b는 1시간 안팎)

```bash
$PY $BR run --model gemini-2.5-flash --repeat 1 --scenario-set 150 --cache-tag codefirst150
$PY $BR run --model gemma4:12b --repeat 1 --scenario-set 150 --cache-tag codefirst150
```
Expected: 시나리오마다 `run: <모델> eNNN rep0 total=… error=None`. 중간에 끊겨도 같은 명령을 다시 돌리면 남은 회차만 돈다.

- [ ] **Step 3: 채점·판정 묶음**

```bash
$PY $BR score --scenario-set 150 --cache-tag codefirst150
$PY $BR judge-export --scenario-set 150 --cache-tag codefirst150
```
Expected: `../data/eval/cache/llm-benchmark/report-codefirst150/score_gemini-2.5-flash.json`·`score_gemma4_12b.json`, `../data/eval/cache/llm-benchmark/judge-codefirst150/packet_e001.md`… 150개 + `mapping.json` + `human_sample.json`(20건). 자동 지표 기대: `answer.digits_after_guard == 0`, `verdict_match == 1.0`(가드가 모순 단락을 내보내지 않는다).

- [ ] **Step 4: Claude 판정 (150건, 해석 단락만)**

판정자 서브에이전트(모델명 가린 묶음, opus)를 묶음 단위로 띄워 `data/eval/report_answer_rubric.md` 기준으로 `judge-codefirst150/verdict_<id>.json`을 쓰게 한다. 모두 모이면 하나로 합쳐 넣는다:

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first
J=data/eval/cache/llm-benchmark/judge-codefirst150
python3 -c "
import json, glob
merged = {}
for path in sorted(glob.glob('$J/verdict_*.json')):
    merged.update(json.load(open(path, encoding='utf-8')))
json.dump(merged, open('$J/verdicts_all.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(merged))"
cd backend && $PY $BR judge-import --file ../$J/verdicts_all.json --cache-tag codefirst150
```
Expected: `150`, `judge-import: 2개 모델 → …/judge-codefirst150/scores.json`

- [ ] **Step 5: 핵심 오류율과 구간 (기준선과 같은 형식 — Clopper-Pearson 95%)**

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first
python3 - <<'EOF'
import json
from math import comb

scores = json.load(open("data/eval/cache/llm-benchmark/judge-codefirst150/scores.json", encoding="utf-8"))

def _cdf(k, n, p):
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))

def clopper_pearson(k, n, alpha=0.05):
    def solve(below_root):  # 단조 함수의 근 — 이분법
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if below_root(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - _cdf(k - 1, n, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _cdf(k, n, p) > alpha / 2)
    return lower, upper

for model, by_sid in sorted(scores.items()):
    n = len(by_sid)
    err = sum(bool(s["core_error"]) for s in by_sid.values())
    answered = sum(bool(s["answered"]) for s in by_sid.values())
    hard = sum(bool(s["hard_to_judge"]) for s in by_sid.values())
    lo, hi = clopper_pearson(err, n)
    print(f"{model}: n={n} 핵심 오류 {err}건 {err / n:.1%} (95% {lo:.1%}~{hi:.1%}) · 질문에 답함 {answered / n:.1%} · 판단 어려움 {hard}건")
EOF
```
(검산: 40/150이면 26.7%, 19.8%~34.5% — 기준선 표기와 같다.)

- [ ] **Step 6: 사람 검수 20건 요청**

`judge-codefirst150/human_sample.json`의 20개 id와 각 `packet_<id>.md` 경로를 사용자에게 보내 해석 단락만(질문에 답했는가·본문과 어긋난 말이 있는가·판단이 어려웠는가) 검수를 요청한다. 받으면 notes에 적는다. 노트를 쓰는 시점까지 받지 못했으면 notes의 해당 절에 "사람 검수: 요청함(human_sample.json 20건), 결과 대기"라고 적고 결과가 오면 같은 파일을 고쳐 다시 커밋한다.

- [ ] **Step 7: 결과 노트 쓰기**

결과 폴더를 만들고 산출물을 복사한다:

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/report-code-first
OUT=data/eval/results/report-code-first-2026-10-05
C=data/eval/cache/llm-benchmark
mkdir -p $OUT
cp $C/report-codefirst150/score_gemini-2.5-flash.json $C/report-codefirst150/score_gemma4_12b.json $C/report-codefirst150/sections_check.json $OUT/
cp $C/judge-codefirst150/scores.json $OUT/judge_scores.json
cp $C/judge-codefirst150/human_sample.json $OUT/
```

`$OUT/notes.md`를 아래 절 구성으로 쓴다(수치는 Step 3·5·6 출력에서 옮긴다 — 추정하지 않는다):

1. `# 리포트 코드 우선 구조 재평가 (2026-10-05, backend v0.68.0)` — 무엇이 바뀌었나(6개 절 코드, 해석 한 단락, 도구 루프 제거) 3줄.
2. `## 비교 대상이 바뀌었다` — 기준선(설계서 §1: 리포트 **전체** 핵심 오류율 Claude 판정 Gemini 26.7% [19.8~34.5]·gemma4:12b 80%)과 이번 판정 대상(**해석 한 단락**)이 다르다는 것, 6개 절은 결정적이라 판정 대상이 아니라는 것을 명시.
3. `## 코드 절 자동 검사` — `sections_check.json`: 150건 중 범위 없는 숫자 줄 N건·이유 빠진 자료 부족 자리 N건.
4. `## 해석 자동 지표` — 표: 모델 | n | 완주 | 폴백 비율 | 가드 뒤 숫자 | 판정 모순(가드 뒤) | 가드 전 모순 시도 비율 | 지운 문장 수 | 해석 첫 글자 p95(ms) | 완료 p95(ms). 첫 글자 지연은 해석 단락 기준이며 본문 6개 절은 사실 수집 직후 즉시라는 주석.
5. `## Claude 판정 (해석 단락, 150건)` — 표: 모델 | 핵심 오류(건·%·95% 구간) | 질문에 답함 | 판단 어려움. 기준선 표기와 같은 형식, 비교 대상 차이 재명시.
6. `## 사람 검수 (20건)` — Step 6 결과 또는 대기 표기.
7. `## 읽기` — 숫자 가드가 정상 문장을 지운 사례("2층"·"24시간" 등, 지운 문장 수 지표)와 폴백이 난 시나리오, 한계(판정자도 LLM, 사람 검수 표본 20건).

- [ ] **Step 8: 버전 로그와 커밋**

`## [v0.68.0]`의 `### Added` 끝에 한 줄(수치는 Step 3·5에서):

```markdown
- 재평가 결과 `data/eval/results/report-code-first-2026-10-05/` — 평가셋 150건 × Gemini·gemma4:12b 각 1회(온도 0·seed 42). 코드 절 자동 검사 문제 0건, 해석 가드 뒤 숫자 0개, Claude 판정 해석 단락 핵심 오류 Gemini ○○%·12b ○○%(기준선은 리포트 전체 26.7%·80% — 비교 대상이 다르다, notes 참고).
```

(`○○`는 Step 5 출력값으로 바꿔 쓴다 — 커밋 전에 남아 있으면 안 된다.)

```bash
git add data/eval/results/report-code-first-2026-10-05 backend/docs/backend_ver_log.md
git commit -m "$(cat <<'EOF'
backend v0.68.0: 리포트 코드 우선 구조 150건 재평가 결과

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

## 설계서 대응표 (self-review)

| 설계서 | 태스크 |
|---|---|
| §2 LLM 범위·질문 없음 총평·도구 제거·샘플링 유지 | Task 3 (`SYSTEM_PROMPT`·`answer_message`·도구 루프 제거), Global Constraints |
| §3 구성·SSE 순서·인용·저장(answer 추가, 옛 저장본) | Task 3 (`run`, `_news_citations`, `SECTION_ORDER`, 라우터 저장 테스트), Task 6 (answer 없으면 블록 생략) |
| §4 코드 섹션 원칙 ①~④·섹션별 내용 | Task 1, Task 4 Step 7(`sections-check` 150건) |
| §5 입력(6개 절 그대로)·출력 규칙·가드 3종·폴백 체인·`agent_tools` 정리 | Task 2, Task 3, Task 5 |
| §6 프론트(`ReportSection`·mock·"해석" 블록·graded-paragraphs 회귀) | Task 6 |
| §7 평가(150건·두 모델 1회·코드 절 자동 검사·해석 자동 지표·사람 20건·기준선 비교 명시) | Task 4, Task 7 |
| §8 TDD·대표 사례만·dict 디스패치·버전 | 전 태스크 |
| §9 문장 조정·숫자 가드 과삭제 지표·옛 저장본·계약 테스트 | Task 4 Step 7, `removed_sentences`, Task 3 라우터 테스트, Task 6 mock 계약 테스트 |

설계서 해석으로 정한 것:
- "둘 다 실패하거나 가드 후 빈 단락이면 코드 한 줄" — 판정 모순·가드 후 빈 단락·호출 실패를 모두 "그 모델 실패 → 다음 모델"로 같게 다룬다. 다음 모델은 운영 hybrid에만 붙고(Gemini 장애로 이미 로컬이 답했으면 같은 모델을 다시 부르지 않는다), 벤치·단일 모델 지정은 그 모델만 평가한다.
- "인용은 사실 묶음에서 코드가 만든 것만" — `facts.news`(RAG 뉴스)를 참고 신호 인용으로 만든다. 다른 사실(판정·공고 등)은 화면 카드가 원문을 보여 주므로 인용에 넣지 않는다.
- "유사 사례 … 최근 뉴스([참고 신호], 없으면 줄 생략)" — `facts.analogs.recent_news`의 유형별 조치 소식 문장(기사 1건 이상일 때만)으로 본다(기존 폴백의 "관련 뉴스 없음" 줄을 생략하는 규칙과 같은 대상).
- 해석은 끝까지 모았다가 내보내므로 스트리밍(`stream()`) 대신 비스트리밍 `chat()`을 쓴다.
