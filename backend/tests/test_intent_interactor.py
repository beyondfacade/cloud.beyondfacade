"""관문 인터랙터 검증 — LLM 폴백 조건·검증·실패 시 규칙 응답, 진단 결합, 두 번째 형태 (Fake 포트)."""

import pytest

from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import (
    IntentLlmPort,
    MasterDictionaryPort,
    ProfileFactsPort,
)
from apps.intent.app.use_cases.intent_interactor import IntentInteractor
from apps.intent.domain.errors import (
    IndustryNotFoundError,
    IntentTextEmptyError,
    RegionNotFoundError,
)
from apps.intent.domain.services.diagnosis import PeakSalesBand, ProfileFacts
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary, RegionEntry

_DICT = MasterDictionary(
    regions=[
        RegionEntry("1168064000", "역삼1동", "11680", "강남구"),
        RegionEntry("1144066000", "서교동", "11440", "마포구"),
        RegionEntry("1168052100", "신사동", "11680", "강남구"),
        RegionEntry("1162055000", "신사동", "11620", "관악구"),
    ],
    districts={"강남구": "11680", "마포구": "11440", "관악구": "11620"},
    industry_names={"cafe": "카페", "hair_salon": "미용실", "karaoke": "노래방"},
)


class FakeMasters(MasterDictionaryPort):
    def load(self) -> MasterDictionary:
        return _DICT


class FakeFacts(ProfileFactsPort):
    def __init__(self, with_peak: bool = True) -> None:
        self.with_peak = with_peak
        self.calls: list[tuple[str, str]] = []

    def latest_profile(self, region_code, region_name):
        return ProfileFacts(
            region_name=region_name,
            type_code="office",
            type_reason="직장인구가 상주인구의 5.9배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다.",
            time_label="day",
            year_quarter="20262",
        )

    def peak_sales_band(self, region_code, industry_id):
        self.calls.append((region_code, industry_id))
        return PeakSalesBand("11_14", "20254") if self.with_peak else None


class FakeLlm(IntentLlmPort):
    def __init__(self, suggestion: LlmSuggestion | None) -> None:
        self._suggestion = suggestion
        self.calls: list[str] = []

    def extract(self, text: str):
        self.calls.append(text)
        return self._suggestion


def _interactor(llm=None, facts=None) -> IntentInteractor:
    return IntentInteractor(FakeMasters(), facts or FakeFacts(), llm or FakeLlm(None))


def test_A유형은_진단이_붙고_규칙_경로면_source가_rule이다():
    result = _interactor().parse("역삼1동에 카페, 예산 5천")

    assert result.intent_type == "A" and result.source == "rule"
    assert result.diagnosis is not None
    assert result.diagnosis.sentence == "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다."
    assert result.missing == []


def test_B유형은_진단이_없고_업종이_결측이다():
    result = _interactor().parse("서교동에서 뭘 하면 좋을까")

    assert result.intent_type == "B"
    assert result.diagnosis is None
    assert result.missing == ["industry", "budget"]


def test_규칙이_동을_찾으면_LLM을_부르지_않는다():
    llm = FakeLlm(LlmSuggestion(region_name="서교동"))

    _interactor(llm=llm).parse("역삼1동 카페")

    assert llm.calls == []


def test_후보가_있어도_LLM을_부르지_않는다():
    # 되묻기로 풀 수 있는 것을 LLM에 묻지 않는다
    llm = FakeLlm(LlmSuggestion(region_name="서교동"))

    result = _interactor(llm=llm).parse("신사동 노래방")

    assert llm.calls == [] and len(result.candidates) == 2


def test_동이_없으면_LLM을_부르고_검증_통과분만_채운다():
    llm = FakeLlm(LlmSuggestion(region_name="서교동", industry_id="hair_salon"))

    result = _interactor(llm=llm).parse("홍대 근처 미용실")

    assert llm.calls == ["홍대 근처 미용실"]
    assert result.region_code == "1144066000"
    assert result.industry_id == "hair_salon"  # 규칙이 이미 잡은 값은 LLM이 덮지 않는다
    assert result.source == "llm"
    assert result.intent_type == "A"


def test_LLM이_없는_동이나_업종을_주면_버린다():
    llm = FakeLlm(LlmSuggestion(region_name="없는동", industry_id="restaurant"))

    result = _interactor(llm=llm).parse("어딘가 식당")

    assert result.region_code is None and result.industry_id is None
    assert result.source == "rule"


def test_LLM_실패는_규칙_응답으로_끝난다():
    result = _interactor(llm=FakeLlm(None)).parse("홍대 근처 미용실")

    assert result.intent_type == "C" and result.source == "rule"
    assert result.industry_id == "hair_salon"


def test_LLM이_동명이동을_주면_후보로_남긴다():
    llm = FakeLlm(LlmSuggestion(region_name="신사동"))

    result = _interactor(llm=llm).parse("가로수길 카페")

    assert result.region_code is None and len(result.candidates) == 2


def test_매출_행이_없으면_뒤_절_없는_진단이다():
    result = _interactor(facts=FakeFacts(with_peak=False)).parse("역삼1동 카페")

    assert result.diagnosis is not None
    assert result.diagnosis.sentence == "역삼1동은 낮 인구 우위형입니다."


def test_빈_문장은_예외다():
    with pytest.raises(IntentTextEmptyError):
        _interactor().parse("   ")


def test_두_번째_형태는_파서를_건너뛰고_진단만_붙인다():
    facts = FakeFacts()

    result = _interactor(facts=facts).diagnose("1168064000", "cafe")

    assert result.intent_type == "A" and result.region_name == "역삼1동"
    assert facts.calls == [("1168064000", "cafe")]
    assert result.diagnosis is not None


def test_두_번째_형태의_없는_코드는_도메인_예외다():
    with pytest.raises(RegionNotFoundError):
        _interactor().diagnose("9999999999", "cafe")
    with pytest.raises(IndustryNotFoundError):
        _interactor().diagnose("1168064000", "restaurant")
