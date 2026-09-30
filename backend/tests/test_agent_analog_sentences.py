from apps.agent.domain.services.analog_sentences import (
    condition_sentence,
    recommended_sentence,
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


def test_자료가_없거나_유형_종합이_없으면_그대로_돌려준다():
    unavailable = {"available": False, "reason": "없음"}
    assert with_sentences(unavailable) is unavailable
    assert with_sentences({"categories": []}) == {"categories": []}
