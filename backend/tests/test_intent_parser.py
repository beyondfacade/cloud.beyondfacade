"""관문 파서 검증 — 규칙 추출기 체인 (DB·LLM 없음, 사전은 순수 인자)."""

from apps.intent.domain.services.extractors import (
    BudgetExtractor,
    IndustryExtractor,
    RegionExtractor,
    run_extractors,
)
from apps.intent.domain.value_objects.intent_draft import IntentDraft
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary, RegionEntry

_REGIONS = [
    RegionEntry("1168064000", "역삼1동", "11680", "강남구"),
    RegionEntry("1168065000", "역삼2동", "11680", "강남구"),
    RegionEntry("1168052100", "신사동", "11680", "강남구"),
    RegionEntry("1162055000", "신사동", "11620", "관악구"),
    RegionEntry("1144072000", "연남동", "11440", "마포구"),
    RegionEntry("1144066000", "서교동", "11440", "마포구"),
    RegionEntry("1111051500", "청운효자동", "11110", "종로구"),
]
_DICT = MasterDictionary(
    regions=_REGIONS,
    districts={"강남구": "11680", "관악구": "11620", "마포구": "11440", "종로구": "11110", "중구": "11140"},
    industry_names={"cafe": "카페", "karaoke": "노래방", "hair_salon": "미용실", "pc_bang": "PC방"},
)


def _run(text: str) -> IntentDraft:
    return run_extractors(
        [RegionExtractor(_DICT), IndustryExtractor(_DICT), BudgetExtractor()], text
    )


def test_A유형_동과_업종과_예산이_한_문장에서_잡힌다():
    draft = _run("연남동에 카페 차리고 싶어, 예산 5천")

    assert draft.region_code == "1144072000"
    assert draft.district_code == "11440"
    assert draft.industry_id == "cafe"
    assert draft.budget_krw == 50_000_000


def test_B유형_동만_있으면_업종은_비어_있다():
    draft = _run("연남동에서 뭘 하면 좋을까")

    assert draft.region_code == "1144072000"
    assert draft.industry_id is None


def test_C유형_예산만_있으면_동도_업종도_비어_있다():
    draft = _run("예산 5천이면 뭐 할 수 있어?")

    assert draft.region_code is None and draft.industry_id is None
    assert draft.budget_krw == 50_000_000


def test_번호가_붙은_동은_기본_이름으로_찾아_후보를_준다():
    # 사람은 "역삼동"이라고 말하지만 마스터에는 역삼1동·역삼2동뿐이다
    draft = _run("역삼동에 카페")

    assert draft.region_code is None
    assert [c.name for c in draft.candidates] == ["역삼1동", "역삼2동"]
    assert draft.district_code == "11680"  # 후보가 한 구에 있으면 구는 확정된다


def test_동명이동은_구_언급이_있으면_그것으로_푼다():
    draft = _run("관악구 신사동 노래방")

    assert draft.region_code == "1162055000"
    assert draft.candidates == ()


def test_동명이동은_구_언급이_없으면_후보_둘을_준다():
    draft = _run("신사동 노래방")

    assert draft.region_code is None
    assert {c.district_name for c in draft.candidates} == {"강남구", "관악구"}
    assert draft.district_code is None  # 구가 갈리면 확정하지 않는다


def test_구만_말하면_구_코드만_잡힌다():
    draft = _run("중구에서 미용실")

    assert draft.region_code is None
    assert draft.district_code == "11140"
    assert draft.industry_id == "hair_salon"


def test_긴_이름이_먼저_맞는다():
    # "청운효자동"이 "효자동"류 부분 문자열로 먼저 잡히지 않아야 한다 — 긴 이름 우선
    draft = _run("청운효자동 카페")

    assert draft.region_code == "1111051500"


def test_업종_동의어와_영문_표기를_알아듣는다():
    assert _run("연남동 커피").industry_id == "cafe"
    assert _run("연남동 피시방").industry_id == "pc_bang"
    assert _run("연남동 PC방").industry_id == "pc_bang"


def test_예산은_큰_단위부터_이어지는_작은_단위를_합산한다():
    assert _run("예산 1억 5천").budget_krw == 150_000_000
    assert _run("예산 1억5천만").budget_krw == 150_000_000
    assert _run("3천만원").budget_krw == 30_000_000


def test_단위_없는_맨숫자는_금액이_아니다():
    draft = _run("연남동 2층에 카페")

    assert draft.budget_krw is None
