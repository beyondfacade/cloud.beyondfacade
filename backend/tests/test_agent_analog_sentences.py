from apps.agent.domain.services.analog_sentences import (
    condition_sentence,
    llm_view,
    news_sentence,
    recommended_sentence,
    summary_sentence,
    with_sentences,
)


def _period(growth: float, excess: float, closure: float) -> dict:
    return {
        "start_month": "2019-01", "end_month": "2019-12", "growth_pct": growth,
        "all_growth_pct": round(growth - excess, 1), "excess_pct": excess,
        "closure_rate_pct": closure, "rank": 1, "industry_count": 12,
    }


def _condition(direction: str, before: dict, recent: dict) -> dict:
    return {
        "event_id": "e", "event_name": "코로나19 국내 유행과 방역 조치 — 첫 확진부터 해제까지",
        "direction": direction, "before": before, "recent": recent,
    }


def _refs(*names: str) -> list[dict]:
    return [{"industry_id": name, "industry_name": name} for name in names]


def test_강세_업종_문장은_유형별_상황과_받침에_맞는_어미로_쓴다():
    assert recommended_sentence({"category": "work_hours", "recommended": _refs("헬스장", "중식", "노래방")}) == (
        "근로시간이 줄었던 시기에 다른 업종보다 상대적으로 잘 버틴 업종은 헬스장, 중식, 노래방이었습니다."
    )
    assert recommended_sentence({"category": "pandemic", "recommended": _refs("양식", "헬스장", "PC방", "카페")}) == (
        "감염병이 유행했던 시기에 다른 업종보다 상대적으로 잘 버틴 업종은 양식, 헬스장, PC방, 카페였습니다."
    )


def test_강세_업종이_없거나_모르는_유형이면_문장을_만들지_않는다():
    assert recommended_sentence({"category": "pandemic", "recommended": []}) is None
    assert recommended_sentence({"category": "unknown", "recommended": _refs("양식")}) is None


def test_직전_비교_문장은_사례_짧은_이름과_더_덜_늘고_줄음과_폐업률_변화를_쓴다():
    condition = _condition("weaker", _period(7.1, 5.8, 14.0), _period(-1.1, -0.1, 20.1))
    assert condition_sentence(condition, "카페") == (
        "코로나19 국내 유행과 방역 조치 직전 1년 카페는 전 업종보다 5.8%p 더 늘었고, "
        "최근 1년은 전 업종과 비슷하게 줄었으며, 폐업률은 14.0%에서 20.1%로 높아졌습니다. "
        "비슷한 충격이 오면 그때보다 약할 수 있습니다."
    )


def test_줄었는데_전_업종보다_덜_줄면_덜_줄었다고_쓰고_방향별_해석을_잇는다():
    condition = _condition("stronger", _period(-2.0, -1.5, 18.0), _period(-0.5, 1.2, 17.8))
    assert condition_sentence(condition, "양식") == (
        "코로나19 국내 유행과 방역 조치 직전 1년 양식은 전 업종보다 1.5%p 더 줄었고, "
        "최근 1년은 전 업종보다 1.2%p 덜 줄었으며, 폐업률은 18.0%에서 17.8%로 비슷했습니다. "
        "그때보다 버틸 여력이 있을 수 있습니다."
    )


def _event(name: str, quarters: int, weak: int, strong: int, streak: int = 0, current: bool = False) -> dict:
    return {
        "name": name, "current": current, "quarters": [{"quarter": i} for i in range(1, quarters + 1)],
        "target_weak_quarters": weak, "target_strong_quarters": strong, "target_weak_streak": streak,
        "series": [{"role": "target", "industry_name": "카페"}],
    }


def test_사례_요약_문장은_이후_분기_수와_약세_강세_분기_수를_쓴다():
    assert summary_sentence(_event("주 52시간제 시행 — 5~49인 사업장", 12, 8, 2, streak=3), "카페") == (
        "주 52시간제 시행 이후 12분기 중 카페가 평소보다 약했던 분기는 8분기, 강했던 분기는 2분기였고, "
        "처음 3분기는 연속으로 약했습니다."
    )
    assert summary_sentence(_event("코로나19 국내 유행과 방역 조치 — 첫 확진부터", 12, 12, 0, streak=12), "양식") == (
        "코로나19 국내 유행과 방역 조치 이후 12분기 내내 양식이 평소보다 약했습니다."
    )
    assert summary_sentence(_event("메르스 유행", 12, 0, 3), "카페") == (
        "메르스 유행 이후 12분기 중 카페가 평소보다 강했던 분기는 3분기였습니다."
    )
    assert summary_sentence(_event("메르스 유행", 4, 0, 0), "카페") == "메르스 유행 이후 4분기 동안 카페는 평소와 비슷했습니다."


def test_진행_중_이벤트는_지금까지로_쓰고_끝난_분기가_없으면_문장을_만들지_않는다():
    assert summary_sentence(_event("최저임금 인상 — 2026년", 2, 0, 2, current=True), "카페") == (
        "최저임금 인상 이후 지금까지 2분기 내내 카페가 평소보다 강했습니다."
    )
    assert summary_sentence(_event("최저임금 인상 — 2026년", 0, 0, 0, current=True), "카페") is None


def _recent(checked: bool, count: int) -> dict:
    return {
        "category": "work_hours", "label": "근로시간", "days": 30, "keywords": ["근로시간 단축", "주4일제"],
        "checked": checked, "article_count": count, "headlines": [],
    }


def test_뉴스_문장은_유형_조치_단어와_건수를_쓴다():
    assert news_sentence(_recent(True, 0)) == "최근 30일 근로시간 단축·주4일제 같은 조치 소식은 없습니다."
    assert news_sentence(_recent(True, 15)) == "최근 30일 근로시간 단축·주4일제 관련 뉴스는 15건입니다."
    assert news_sentence(_recent(False, 0)) == "근로시간 최근 소식은 확인하지 못했습니다."


def test_사례_이름은_짧은_구분어를_괄호로_남기고_같은_이름끼리는_연도로_가른다():
    wages = [
        {**_event("최저임금 인상 — 2026년 시급 10,320원(+2.9%)", 2, 0, 2, current=True), "event_id": "w26", "start_date": "2026-01-01"},
        {**_event("최저임금 인상 — 2025년 시급 10,030원(+1.7%)", 4, 1, 1), "event_id": "w25", "start_date": "2025-01-01"},
    ]
    hours = {**_event("주 52시간제 시행 — 5~49인 사업장", 12, 8, 2), "event_id": "h", "start_date": "2021-07-01"}
    covid = {**_event("코로나19 국내 유행과 방역 조치 — 첫 확진부터 사회적 거리두기 전면 해제까지", 12, 12, 0), "event_id": "c", "start_date": "2020-01-20"}
    enriched = with_sentences({"current_events": wages[:1], "analogs": [wages[1], hours, covid]})
    sentences = [e["summary_sentence"] for e in [*enriched["current_events"], *enriched["analogs"]]]
    assert sentences[0].startswith("2026년 최저임금 인상 이후 지금까지")
    assert sentences[1].startswith("2025년 최저임금 인상 이후 4분기")
    assert sentences[2].startswith("주 52시간제 시행(5~49인 사업장) 이후 12분기")
    assert sentences[3].startswith("코로나19 국내 유행과 방역 조치 이후 12분기")


def test_계산_범위가_있으면_내_업종_문장에_범위를_붙이고_비교_업종은_서울_전체라고_쓴다():
    condition = _condition("weaker", _period(7.1, 5.8, 14.0), _period(-1.1, -0.1, 20.1))
    analogs = {
        "scope": {"level": "district", "name": "관악구", "comparison_name": "서울 전체"},
        "current_events": [_event("최저임금 인상 — 2026년", 2, 0, 0, current=True)],
        "analogs": [_event("메르스 유행", 12, 0, 3)],
        "outlooks": [{"category": "pandemic", "recommended": _refs("양식"), "condition": condition}],
    }
    enriched = with_sentences(analogs)
    assert enriched["current_events"][0]["summary_sentence"] == (
        "최저임금 인상(2026년) 이후 지금까지 2분기 동안 관악구 카페는 평소와 비슷했습니다."
    )
    assert enriched["analogs"][0]["summary_sentence"] == (
        "메르스 유행 이후 12분기 중 관악구 카페가 평소보다 강했던 분기는 3분기였습니다."
    )
    outlook = enriched["outlooks"][0]
    assert outlook["recommended_sentence"] == (
        "감염병이 유행했던 시기에 서울 전체에서 다른 업종보다 상대적으로 잘 버틴 업종은 양식이었습니다."
    )
    assert outlook["condition_sentence"].startswith("코로나19 국내 유행과 방역 조치 직전 1년 관악구 카페는 전 업종보다")


def test_서울_전체로_계산했으면_내_업종_문장에_서울_전체라고_쓴다():
    analogs = {
        "scope": {"level": "seoul", "name": "서울 전체", "comparison_name": "서울 전체"},
        "analogs": [_event("메르스 유행", 12, 0, 3)],
    }
    assert with_sentences(analogs)["analogs"][0]["summary_sentence"] == (
        "메르스 유행 이후 12분기 중 서울 전체 카페가 평소보다 강했던 분기는 3분기였습니다."
    )


def test_사례와_뉴스에도_코드가_만든_문장을_붙인다():
    analogs = {
        "current_events": [_event("최저임금 인상 — 2026년", 2, 0, 2, current=True)],
        "analogs": [_event("주 52시간제 시행 — 5~49인 사업장", 12, 8, 2)],
        "outlooks": [],
        "recent_news": [_recent(True, 15)],
    }
    enriched = with_sentences(analogs)
    assert enriched["current_events"][0]["summary_sentence"].startswith("최저임금 인상(2026년) 이후 지금까지")
    assert enriched["analogs"][0]["summary_sentence"].startswith("주 52시간제 시행(5~49인 사업장) 이후 12분기")
    assert enriched["recent_news"][0]["sentence"] == "최근 30일 근로시간 단축·주4일제 관련 뉴스는 15건입니다."
    assert "summary_sentence" not in analogs["analogs"][0]


def test_요약_문장은_질문_속_유형의_최근_사례_2건과_진행_중_이벤트에만_붙인다():
    def event(event_id: str, category: str, current: bool = False) -> dict:
        return {**_event(f"{event_id} 사례", 4, 1, 1, current=current), "event_id": event_id, "category": category}

    enriched = with_sentences({
        "categories": [
            {"category": "work_hours", "reason": "question"}, {"category": "minimum_wage", "reason": "current"},
        ],
        "current_events": [event("w26", "minimum_wage", current=True)],
        "analogs": [
            event("h21", "work_hours"), event("h20", "work_hours"), event("h18", "work_hours"),
            event("w25", "minimum_wage"), event("w24", "minimum_wage"),
        ],
    })
    written = [e["event_id"] for e in [*enriched["current_events"], *enriched["analogs"]] if e["summary_sentence"]]
    assert written == ["w26", "h21", "h20"]  # 진행 중 유형은 지난 사례 대신 진행 중 이벤트로 쓴다


def test_LLM에게는_요약_문장을_붙인_사례만_넘긴다():
    enriched = {
        "analogs": [{"event_id": "h21", "summary_sentence": "문장"}, {"event_id": "h18", "summary_sentence": None}],
        "current_events": [{"event_id": "w26", "summary_sentence": "문장"}],
    }
    assert [e["event_id"] for e in llm_view(enriched)["analogs"]] == ["h21"]
    assert llm_view(enriched)["current_events"] == enriched["current_events"]
    assert len(enriched["analogs"]) == 2  # 화면용 원본은 그대로
    plain = {"analogs": [{"event_id": "x"}]}  # 문장을 붙이기 전 자료는 거르지 않는다
    assert llm_view(plain) == plain
    assert llm_view({"available": False}) == {"available": False}


def test_겹친_정책_문장은_앞_2개_분기만_쓰고_나머지는_분기_수로_줄인다():
    def quarter(label: str, overlaps: list[str]) -> dict:
        return {"label": label, "overlaps": overlaps}

    event = {
        **_event("코로나19 유행", 12, 12, 0), "event_id": "c",
        "quarters": [
            quarter("1년 차 1분기", ["최저임금 인상 — 2020년 시급 8,590원(+2.9%)", "주 52시간제 시행 — 50~299인 사업장"]),
            quarter("1년 차 2분기", ["1차 긴급재난지원금 지급 (전 국민)"]),
            quarter("1년 차 3분기", []),
            quarter("2년 차 1분기", ["최저임금 인상 — 2021년 시급 8,720원(+1.5%)"]),
            quarter("2년 차 4분기", ["소상공인 손실보상제 시행"]),
        ],
    }
    enriched = with_sentences({"analogs": [event]})["analogs"][0]
    assert enriched["overlap_sentence"] == (
        "같은 기간 1년 차 1분기에는 최저임금 인상·주 52시간제 시행(50~299인 사업장), "
        "1년 차 2분기에는 1차 긴급재난지원금 지급 (전 국민)도 있었습니다. 그 밖에 2개 분기에도 다른 정책이 겹쳤습니다."
    )
    quiet = with_sentences({"analogs": [{**event, "quarters": [quarter("1년 차 1분기", [])]}]})["analogs"][0]
    assert quiet["overlap_sentence"] is None


def test_겹친_정책_이름은_긴_설명을_떼고_짧은_구분어만_남긴다():
    event = {
        **_event("주 52시간제 시행 — 5~49인 사업장", 4, 1, 1), "event_id": "h",
        "quarters": [{"quarter": 1, "overlaps": [
            "최저임금 인상 — 2022년 시급 9,160원(+5.1%)", "주 52시간제 시행 — 50~299인 사업장", "1차 긴급재난지원금 지급 (전 국민)",
        ]}],
    }
    enriched = with_sentences({"analogs": [event]})
    assert enriched["analogs"][0]["quarters"][0]["overlaps"] == [
        "최저임금 인상", "주 52시간제 시행(50~299인 사업장)", "1차 긴급재난지원금 지급 (전 국민)",
    ]
    assert event["quarters"][0]["overlaps"][0].startswith("최저임금 인상 — ")  # 원본은 그대로


def test_유형_종합마다_코드가_만든_문장을_붙이고_비교가_없으면_비워_둔다():
    analogs = {
        "analogs": [{"series": [{"role": "target", "industry_name": "카페"}]}],
        "outlooks": [
            {
                "category": "pandemic", "recommended": _refs("양식"),
                "condition": _condition("similar", _period(1.0, 0.2, 15.0), _period(0.8, 0.0, 15.2)),
            },
            {"category": "minimum_wage", "recommended": _refs("PC방"), "condition": None},
        ],
    }
    pandemic, minimum_wage = with_sentences(analogs)["outlooks"]
    assert pandemic["recommended_sentence"].endswith("잘 버틴 업종은 양식이었습니다.")
    assert pandemic["condition_sentence"].endswith("업종 상태는 그때와 비슷합니다.")
    assert "카페는" in pandemic["condition_sentence"]
    assert minimum_wage["condition_sentence"] is None
    assert "condition_sentence" not in analogs["outlooks"][0]  # 원본은 건드리지 않는다


def test_자료가_없으면_그대로_돌려준다():
    unavailable = {"available": False, "reason": "없음"}
    assert with_sentences(unavailable) is unavailable
    assert with_sentences({"categories": []}) == {"categories": []}  # 없는 목록은 만들지 않는다
