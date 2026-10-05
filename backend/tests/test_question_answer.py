"""question_answer — 질문 유형별 직접 답(첫 문장)과 근거 줄 (facts만, LLM·DB 없음)."""

import json
from pathlib import Path

from apps.agent.domain.services.question_answer import BUDGET_GAP, LOAN_NOTE, answer_lead, won
from apps.agent.domain.services.question_topic import QuestionTopic

# 평가셋 고정 facts(e001 송정동 한식, 판정 red — 순유출·조기 폐업 strong, 포화 off)
_BASE = json.loads(
    (Path(__file__).resolve().parents[2] / "data/eval/report_facts_150/e001.json").read_text(encoding="utf-8")
)
_FINANCE = {
    "available": True,
    "expected_monthly_revenue": {"value": 4325694.0, "unit": "원/월", "caveat": "편차가 큽니다.",
                                 "basis": {"year_quarter": "20254", "store_count": 13}},
    "rent_per_m2": {"value": 49.33, "unit": "천원/㎡/월", "caveat": "행정동 단위 임대료 자료가 없어 권역 평균입니다.",
                    "basis": {"region_path": "서울>기타", "period": "2026Q2"}},
    "loan_rate": {"value": 0.0405, "unit": "비율", "caveat": "공시 평균 금리입니다.",
                  "basis": {"period": "202608", "rate_pct": 4.05}},
}


def _facts(**overrides) -> dict:
    return {**_BASE, "finance": _FINANCE, **overrides}


def _verdict(code: str) -> dict:
    return {**_BASE["verdict"], "verdict_code": code}


def test_비추천은_권하지_않는다와_켜진_신호를_첫_문장에_쓴다():
    lead = answer_lead(_facts(), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 권하지 않습니다 — 켜진 경고 신호 2개(순유출, 조기 폐업)."


def test_조건부는_먼저_확인할_신호를_쓴다():
    lead = answer_lead(_facts(verdict=_verdict("orange")), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 조건부입니다 — 순유출, 조기 폐업을 먼저 확인해야 합니다."


def test_경고_없음은_장사가_된다는_근거가_아니라고_쓴다():
    lead = answer_lead(_facts(verdict=_verdict("clear")), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 경고 신호가 없습니다 — 다만 이것이 장사가 된다는 근거는 아닙니다."


def test_일반_질문은_넘지_않은_기준과_점포당_매출을_근거로_든다():
    text = answer_lead(_facts(), QuestionTopic("general"))
    assert "- [확인된 사실] 넘지 않은 경고 기준(송정동 한식): 포화." in text
    assert "점포당 월 평균 매출(송정동 한식, 2025년 4분기, 점포 13곳 평균): 약 433만 원" in text


def test_예산_질문은_예산으로_시작하고_충분한지는_판단할_수_없다고_쓴다():
    text = answer_lead(_facts(budget=50_000_000), QuestionTopic("budget"))
    lead = text.split("\n")[0]
    assert lead.startswith("[확인된 사실] 예산 5,000만 원으로 보면 송정동 한식은 권하지 않습니다")
    assert lead.endswith("예산이 충분한지는 이 리포트로 판단할 수 없습니다.")
    assert "상가 임대료(서울 기타 권역, 2026Q2): ㎡당 월 약 4.9만 원" in text
    assert f"- {BUDGET_GAP}" in text


def test_대출_질문은_전국_공시_금리와_상환_안내를_쓴다():
    text = answer_lead(_facts(), QuestionTopic("loan"))
    assert text.startswith("[확인된 사실] 대출을 끼고 시작한다면 송정동 한식은")
    assert "대출 금리(한국은행 ECOS 전국 공시 평균, 2026년 8월): 연 4.05% — 예상치이며 실제 심사 금리와 다릅니다." in text
    assert f"- {LOAN_NOTE}" in text


def test_프리필이_없으면_그_줄은_자료_부족이다():
    text = answer_lead(_facts(finance={"available": False, "reason": "프리필 조회 실패"}), QuestionTopic("budget"))
    assert "점포당 월 평균 매출(송정동 한식): 자료 부족 — 프리필 조회 실패" in text


def test_금액은_억과_만_원으로_쓴다():
    assert [won(50_000_000), won(100_000_000), won(150_000_000)] == ["5,000만 원", "1억 원", "1억 5,000만 원"]


_BANDS = {
    "available": True,
    "year_quarter": "20254",
    "bands": [
        {"hour_band": "11_14", "footfall_intensity": 0.989, "sales_intensity": 0.346},
        {"hour_band": "21_24", "footfall_intensity": 1.005, "sales_intensity": 2.377},
        {"hour_band": "00_06", "footfall_intensity": 1.029, "sales_intensity": 0.281},
    ],
}


def test_점심_질문은_그_구간의_사람_흐름과_매출_강도를_쓴다():
    text = answer_lead(_facts(hour_gap=_BANDS), QuestionTopic("hours", "lunch"))
    assert text.startswith("[확인된 사실] 점심(11~14시) 위주로 보면 송정동 한식은")
    assert "점심(11~14시)(송정동 유동인구·한식 매출, 2025년 4분기): 사람 흐름은 시간당 하루 평균의 0.99배, 매출은 0.35배." in text


def test_밤_질문은_밤과_새벽_두_구간을_쓴다():
    text = answer_lead(_facts(hour_gap=_BANDS), QuestionTopic("hours", "night"))
    assert "밤(21~24시)(송정동" in text and "새벽(00~06시)(송정동" in text


def test_시간대_자료가_없으면_자료_부족과_동_사람_흐름을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("hours", "evening"))  # e001은 hour_gap 없음
    assert "시간대(송정동 한식): 자료 부족 — 시간대 어긋남 자료가 없다" in text
    assert "사람 흐름(송정동 동 전체, 2026년 2분기): 가장 많은 때" in text


def test_주말_질문은_주말_평일_비를_같은_유형_중앙값과_비교한다():
    text = answer_lead(_facts(), QuestionTopic("hours", "weekend"))
    assert "주말(송정동 동 전체, 2026년 2분기): 주말 하루 유동인구는 평일 하루의 0.99배 — 같은 유형(주거형) 251개 동 중앙값 1.04배." in text


def test_경쟁_질문은_포화_근거와_점포_수_추이와_순유출을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("competition"))
    assert "- [확인된 사실] 포화(송정동 한식): " in text
    assert "송정동 한식 점포 수: 2024년 42곳 → 2025년 42곳 → 2026년(올해 현재까지) 33곳." in text
    assert "- [확인된 사실] 순유출(송정동 한식): " in text


def test_외국인_질문은_주민_연령과_외국인_자료_없음을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("customers", "foreign"))
    assert "주민(송정동, " in text
    assert "유동인구 연령 상위(송정동 동 전체, 2026년 2분기): 20대 22%, 30대 20%." in text
    assert "직장인구 ÷ 상주인구(송정동, 2026년 2분기): 0.08배." in text
    assert "- [확인된 사실] 외국인 주민·방문객 자료는 없습니다." in text
    assert "외국인" not in answer_lead(_facts(), QuestionTopic("customers"))


def test_코로나_질문은_코로나_전후_폐업률과_최근_완결_연도를_쓴다():
    text = answer_lead(_facts(), QuestionTopic("covid"))
    assert "송정동 한식 연간 폐업률(코로나 전후): 2019년 2.8% · 2020년 17.1% · 2021년 9.8% · 2022년 16.7% · 2023년 2.7%." in text
    assert "송정동 한식 최근 완결 연도(2025년) 폐업률: 19.0%." in text
