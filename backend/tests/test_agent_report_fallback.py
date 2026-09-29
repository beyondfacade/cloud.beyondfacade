"""report_fallback — LLM이 빼먹은 판정·대안 절을 facts로 채우는 순수 포매터 (의존성 없음)."""

from apps.agent.domain.services.report_fallback import (
    alternatives_markdown,
    verdict_markdown,
)

_VERDICT = {
    "available": True,
    "region_code": "1168064000",
    "industry_id": "korean_food",
    "verdict_code": "red",
    "strong_count": 2,
    "on_count": 3,
    "signals": [
        {"key": "survival_cliff", "level": "strong", "evidence": "3년 생존율 41%입니다.", "advisory": False},
        {"key": "net_outflow", "level": "on", "evidence": "순유출률 -12%입니다.", "advisory": False},
        {"key": "saturation", "level": "off", "evidence": "포화 아님.", "advisory": False},
        {"key": "shrinking", "level": "on", "evidence": "상권변화지표가 '상권축소'입니다.", "advisory": True},
    ],
    "computed_at": "2026-09-29T03:00:00",
}

_ALTERNATIVES = {
    "available": True,
    "industries": [
        {"industry_id": "bakery", "industry_name": "제과점", "verdict_code": "clear"},
        {"industry_id": "cafe", "industry_name": "카페", "verdict_code": "orange"},
        {"industry_id": "hair_salon", "industry_name": "미용실", "verdict_code": "clear"},
        {"industry_id": "academy", "industry_name": "학원", "verdict_code": "clear"},
    ],
    "regions": [
        {"region_code": "1168065000", "region_name": "역삼2동", "verdict_code": "orange"},
    ],
}


def test_판정_폴백은_배지_한_줄과_켜진_신호_근거를_옮긴다():
    markdown = verdict_markdown(_VERDICT)

    assert "비추천" in markdown.splitlines()[2]
    assert "3년 생존율 41%입니다." in markdown
    assert "순유출률 -12%입니다." in markdown
    assert "포화 아님." not in markdown  # off 신호는 켜진 신호가 아니다


def test_판정_폴백은_참고_신호를_켜진_신호와_섞지_않는다():
    markdown = verdict_markdown(_VERDICT)

    참고줄 = [line for line in markdown.splitlines() if "상권축소" in line][0]
    assert 참고줄.startswith("참고:")


def test_판정_폴백은_산출일을_마지막에_적는다():
    assert verdict_markdown(_VERDICT).splitlines()[-1] == "산출일 2026-09-29T03:00:00"


def test_판정이_없으면_이유와_함께_판정_없음이라고_쓴다():
    markdown = verdict_markdown({"available": False, "reason": "판정 대상 업종이 아니다"})

    assert "판정 없음" in markdown
    assert "판정 대상 업종이 아니다" in markdown
    assert "비추천" not in markdown


def test_켜진_신호가_없으면_신호를_지어내지_않는다():
    markdown = verdict_markdown(
        {
            "available": True,
            "verdict_code": "clear",
            "strong_count": 0,
            "on_count": 0,
            "signals": [{"key": "saturation", "level": "off", "evidence": "포화 아님.", "advisory": False}],
            "computed_at": "2026-09-29T03:00:00",
        }
    )

    assert "경고 없음" in markdown
    assert "켜진 신호 없음" in markdown
    assert "포화 아님." not in markdown


def test_facts_자체가_없으면_폴백_문장을_만들지_않는다():
    assert verdict_markdown(None) is None
    assert verdict_markdown({}) is None
    assert alternatives_markdown(None) is None


def test_대안_폴백은_두_축을_각_최대_3개까지_순서대로_옮긴다():
    markdown = alternatives_markdown(_ALTERNATIVES)

    assert markdown.index("제과점") < markdown.index("카페") < markdown.index("미용실")
    assert "학원" not in markdown  # 네 번째는 자른다
    assert "역삼2동" in markdown
    assert "경고 없음" in markdown and "조건부" in markdown


def test_빈_축은_대안_없음이라고_쓴다():
    markdown = alternatives_markdown({"available": True, "industries": [], "regions": []})

    assert markdown.count("대안 없음") == 2


def test_대안이_없으면_이유와_함께_대안_없음이라고_쓴다():
    markdown = alternatives_markdown({"available": False, "reason": "기준 판정이 없다"})

    assert "대안 없음" in markdown
    assert "기준 판정이 없다" in markdown
