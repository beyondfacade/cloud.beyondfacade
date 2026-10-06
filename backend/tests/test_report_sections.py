"""report_sections — 리포트 6개 절을 facts만으로 쓰는 순수 모듈 (LLM·DB 없음)."""

import json
from pathlib import Path

from apps.agent.domain.services.report_guards import FUNDING_DISCLAIMER
from apps.agent.domain.services.report_sections import (
    SECTION_TITLES,
    alternatives_pointer,
    build_sections,
    hour_gap_sentence,
    resident_line,
    scarce_lead,
    scarcity,
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
        _signal("tobacco_gap", "strong", "이 동 상가 자리 200곳 중 75%가 영업 중인 담배소매인 50m 안 — 새 담배소매인 지정이 어렵다", advisory=True),
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


def test_판정은_켜진_신호와_기준을_넘지_않은_신호와_자료_부족_신호를_나눠_쓴다():
    # 한 줄로 묶으면 해석이 "경고 없음은 자료가 비어서"로 읽었다 — 계산해서 꺼진 신호를 이름으로 따로 쓴다
    assert _body("verdict", verdict=_RED) == (
        "[확인된 사실] 송정동 한식 판정: **비추천** — 경고 신호 3개 중 2개 켜짐(강한 신호 2개). "
        "계산했지만 기준을 넘지 않은 신호 1개(포화). 자료 부족으로 계산하지 못한 신호 1개(생존 절벽). "
        "산출 2026-10-04."
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
        "- [확인된 사실] 생존 절벽(송정동 한식 — 3년 전 새로 연 점포 중 지금 남은 비율): "
        "표본 부족 — 3년 전 개업 코호트 1곳 (10곳 미만)\n"
        "- [확인된 사실] 참고 — 담배권 빈자리: 이 동 상가 자리 200곳 중 75%가 영업 중인 담배소매인 50m 안 — 새 담배소매인 지정이 어렵다\n\n"
        "[확인된 사실] 송정동 한식 점포 수·연간 폐업률(해마다): 2019년 점포 41곳·폐업률 2.8% · "
        "2021년 점포 42곳·폐업률 9.8%(재난지원 시기 — 폐업이 늦춰져 왜곡됐을 수 있음) · 2025년 점포 42곳·폐업률 19.1%.\n\n"
        "[확인된 사실] 외부 충격(한식 전용 기록은 없어 전 업종 공통 충격): 최저임금 인상(2019년)."
    )


def test_연간_폐업률은_해마다_값을_싣고_재난지원_단서는_2020_2022년_값_옆에만_붙인다():
    # 두 해 값만 주면 "꾸준히 증가"로 옮겼다(wording 평가 Gemini 6건) — 점포 수도 해마다. 단서를 문장 끝에 두면 12b가 2026년에도 옮겼다
    history = [{"year": 2021, "closure_rate": 0.05, "store_count": 30},
               {"year": 2026, "closure_rate": 0.013, "store_count": 33}]
    body = _body("reasons", verdict=_RED, metrics_history=history, shocks=[])

    assert (
        "점포 수·연간 폐업률(해마다): 2021년 점포 30곳·폐업률 5.0%(재난지원 시기 — 폐업이 늦춰져 왜곡됐을 수 있음) · 2026년(올해 현재까지) 점포 33곳·폐업률 1.3%."
    ) in body


def test_조기_폐업은_생존_절벽과_다른_지표임을_뜻으로_밝힌다():
    # 12b가 조기 폐업(폐업 점포의 영업 기간)으로 표본 부족인 생존 절벽(개업 점포의 생존)을 메웠다(risk-band 평가 4건)
    verdict = {**_RED, "signals": [_signal("early_closure", "on", "최근 3년 폐업 한식의 영업 기간 중위 33개월")]}

    assert _body("reasons", verdict=verdict, shocks=[]).startswith(
        "- [확인된 사실] 조기 폐업(송정동 한식 — 최근 3년 문 닫은 점포가 문 닫기 전까지 영업한 기간, "
        "새로 연 점포의 생존율이 아님): 최근 3년 폐업 한식의 영업 기간 중위 33개월"
    )


def test_연도별_폐업률이_없으면_자료_부족이라고_쓴다():
    body = _body("reasons", verdict=_RED, metrics_history={"available": False, "reason": "조회 실패"}, shocks=[])

    assert "[확인된 사실] 송정동 한식 연간 폐업률: 자료 부족 — 조회 실패" in body
    assert "[확인된 사실] 외부 충격(한식): 자료 부족 — 기록 없음" in body


def test_유사_사례는_질문_속_유형부터_고정_문장만_옮기고_뉴스는_넣지_않는다():
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
        "[확인된 사실] 코로나 문장. 겹친 정책 문장. 강세 업종 문장.\n\n"
        "[확인된 사실] 최저임금 문장."
    )


def test_시간대_문장은_프론트와_같은_입력에_같은_문장을_낸다():
    # frontend/src/features/agent-report/lib/hour-gap-sentence.test.ts 와 같은 세 입력·같은 기대 문장
    cafe = [_band("00_06", 0.3, 0.05), _band("06_11", 1.0, 0.7), _band("11_14", 1.39, 2.99),
            _band("14_17", 1.4, 1.6), _band("17_21", 1.1, 1.2), _band("21_24", 0.5, 0.35)]
    # 사람 흐름과 매출을 두 문장으로 — 한 문장이면 LLM이 "저녁에 사람과 매출이 몰린다"로 합친다(risk-band 평가 4건)
    assert hour_gap_sentence(cafe) == (
        "사람(유동인구)이 가장 많은 때는 오후(14~17시)입니다. "
        "매출이 가장 많은 때는 점심(11~14시)으로, 사람이 가장 많은 때와 다릅니다."
    )
    assert hour_gap_sentence([_band("06_11", 0.8, 0.6), _band("17_21", 1.6, 1.9)]) == (
        "사람(유동인구)과 매출이 모두 저녁(17~21시)에 가장 많습니다."
    )
    assert hour_gap_sentence([_band("06_11", 1.5, 1.2), _band("11_14", 1.6, 1.1)]) == (
        "사람(유동인구)이 가장 많은 때는 점심(11~14시)입니다. "
        "매출이 가장 많은 때는 아침(06~11시)으로, 사람이 가장 많은 때와 다릅니다."
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
        "사람 흐름: 가장 많은 때 밤(21~06시), 가장 적은 때 저녁(17~21시).\n\n"
        "[확인된 사실] 상권 영업 기간(송정동 상권 전체·업종 무관, 2026년 2분기): 영업 중 점포 평균 124개월, "
        "폐업 점포 평균 54개월 — 서울 동 상권 전체 기준값은 118개월·54개월입니다. 상권변화지표: 정체.\n\n"
        "[확인된 사실] 주민(송정동, 2026년 6월 주민등록): 60세 이상 32%, 20~39세 31%."
    )


def test_절_하나를_쓰다_예외가_나면_그_절만_자료_부족으로_쓴다():
    change = {"available": True, "year_quarter": "20262", "change_name": "정체", "operating_months": 124.0,
              "closed_months": 54.0, "seoul": {"operating_months": None, "closed_months": None}}

    sections = build_sections({**_BASE, "commerce_change": change})

    assert sections["conditions"].split("\n\n", 1)[1].startswith("[확인된 사실] 자료 부족 — ")
    assert sections["verdict"] == build_sections(_BASE)["verdict"]


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


def test_시간대_자료_부족_이유에서_내부_코드를_뺀다():
    body = _body("conditions", hour_gap={"available": False, "reason": "시간대 어긋남 자료가 없다: 1120072000 × korean_food"})

    assert body.startswith("[확인된 사실] 시간대(송정동 한식): 자료 부족 — 시간대 어긋남 자료가 없다\n\n")
    assert "1120072000" not in body and "korean_food" not in body


def test_올해_부분연도_폐업률은_올해_현재까지로_표기한다():
    history = [
        {"year": 2019, "store_count": 41, "closure_rate": 0.0278},
        {"year": 2026, "store_count": 33, "closure_rate": 0.30952380952380953},
    ]

    body = _body("reasons", metrics_history=history)  # _BASE의 상권 분기 자료가 20262

    assert "2019년 점포 41곳·폐업률 2.8% · 2026년(올해 현재까지) 점포 33곳·폐업률 31.0%." in body


def test_접수_기간_원문이_상시_접수면_접수를_다시_붙이지_않는다():
    candidates = [{"title": "상시 공고", "org": "서울특별시", "deadline": None, "apply_period": "상시 접수"}]

    assert "- 「상시 공고」 — 서울특별시, 상시 접수\n" in _body("funding", funding_candidates=candidates)


def test_유사_사례_고정_문장_속_업종_id는_업종_이름으로_바꾼다():
    region = {"code": "1126057500", "name": "면목제3.8동", "industry_id": "convenience_store", "industry_name": "편의점"}
    analogs = {"categories": [{"category": "minimum_wage", "reason": "current"}],
               "current_events": [{"category": "minimum_wage", "summary_sentence": "서울 전체 convenience_store는 평소와 비슷했습니다.",
                                   "overlap_sentence": None}]}

    assert _body("analogs", region=region, analogs=analogs) == "[확인된 사실] 서울 전체 편의점은 평소와 비슷했습니다."


def _facts_150(scenario_id: str) -> dict:
    return json.loads(
        (Path(__file__).resolve().parents[2] / f"data/eval/report_facts_150/{scenario_id}.json").read_text(encoding="utf-8")
    )


def test_판정_보류_동네는_계산_못_한_신호와_빠진_자료를_첫_문장에_적는다():
    facts = _facts_150("e007")  # 신월3동 분식 — 판정 보류

    missing = scarcity(facts)

    assert missing == ["폐업·개업 흐름", "개업 점포 생존율", "폐업 점포 영업 기간", "시간대별 매출"]
    assert scarce_lead(facts, missing) == (
        "[확인된 사실] 신월3동 분식은 자료가 부족해 진입 판단을 내리기 어렵습니다 — "
        "부족한 자료: 폐업·개업 흐름, 개업 점포 생존율, 폐업 점포 영업 기간, 시간대별 매출."
    )


def test_판정을_내리지_않는_업종은_부족한_자료_대신_비판정_문장을_쓴다():
    facts = _facts_150("e009")  # 면목제3.8동 편의점 — 판정 대상 업종이 아니다

    assert scarce_lead(facts, scarcity(facts)) == (
        "[확인된 사실] 면목제3.8동 편의점은 경고 판정을 내리는 업종이 아니어서 진입 판단을 내리지 않습니다 — "
        "아래 사실만 참고하세요."
    )


def test_판정이_난_동네는_자료_부족이_아니다():
    assert scarcity(_BASE) is None  # 송정동 한식 — 비추천


def test_대안에_경고_없음이_있으면_대안_절_안내_문장을_쓰고_없으면_쓰지_않는다():
    clear = {"available": True, "industries": [{"verdict_code": "orange"}], "regions": [{"verdict_code": "clear"}]}
    none = {"available": True, "industries": [{"verdict_code": "orange"}], "regions": []}

    assert alternatives_pointer({"alternatives": clear}) == "대안 동네·업종 절에 경고 없음으로 나온 곳도 함께 확인해 보세요."
    assert alternatives_pointer({"alternatives": none}) is None
    assert alternatives_pointer({"alternatives": _UNAVAILABLE}) is None


def test_그래도_한다면에_주민_연령과_아파트_시가를_쓴다():
    facts = {
        **_BASE,
        "population": {"period": "202606", "age_distribution": {"10": 20, "20": 30, "35": 10, "60": 25, "85": 15}},
        "profile": {**_BASE["profile"], "apartment_avg_price_won": 480_839_259},
    }
    assert resident_line(facts) == (
        "[확인된 사실] 주민(송정동, 2026년 6월 주민등록): 60세 이상 40%, 20~39세 40%"
        " · 아파트 평균 시가 약 4.8억 원(동별 편차가 커 참고값입니다)."
    )
    assert resident_line(facts) in build_sections(facts)["conditions"]


def test_뉴스는_본문에_넣지_않는다():
    """본문은 해석 LLM 입력이다 — 네이버 검색 결과는 화면 링크로만 쓴다(검색 API 특약 2.3)."""
    link = {"title": "송정동 골목 상점가 지정", "url": "u1", "published_at": "2026-09-01", "press": None}
    sections = build_sections({**_BASE, "news": [link]})
    assert not any("송정동 골목 상점가" in body or "뉴스" in body for body in sections.values())
