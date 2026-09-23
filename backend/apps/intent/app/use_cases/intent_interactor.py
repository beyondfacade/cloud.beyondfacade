"""관문 인터랙터 — 규칙 추출기 체인 + LLM 폴백 + 결과 조립 (설계서 §5·§6)."""

from apps.intent.app.dtos.intent_dto import (
    DiagnosisDto,
    IntentResultDto,
    LlmSuggestion,
    RegionCandidateDto,
)
from apps.intent.app.ports.input.intent_use_case import IntentUseCase
from apps.intent.app.ports.output.intent_port import (
    IntentLlmPort,
    MasterDictionaryPort,
    ProfileFactsPort,
)
from apps.intent.domain.errors import (
    IndustryNotFoundError,
    IntentTextEmptyError,
    RegionNotFoundError,
)
from apps.intent.domain.services.diagnosis import Diagnosis, compose_diagnosis
from apps.intent.domain.services.extractors import (
    BudgetExtractor,
    IndustryExtractor,
    IntentExtractor,
    RegionExtractor,
    resolve_region,
    run_extractors,
)
from apps.intent.domain.value_objects.intent_draft import IntentDraft
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary


class LlmFallbackExtractor(IntentExtractor):
    """체인의 마지막 — 규칙이 동을 못 찾았을 때만 LLM을 부르고, 준 값은 마스터로 검증한다.

    도메인 추출기가 아니라 여기(app) 있는 이유는 포트가 필요해서다. 검증에서 떨어진 값은 버린다 —
    "홍대"를 "서교동"으로 옮기는 건 LLM의 몫이지만, 없는 동을 지어내는 건 통과시키지 않는다.
    """

    def __init__(self, llm: IntentLlmPort, dictionary: MasterDictionary) -> None:
        self._llm = llm
        self._dictionary = dictionary

    def extract(self, draft: IntentDraft, text: str) -> IntentDraft:
        if draft.region_code is not None or draft.candidates:
            return draft
        suggestion = self._llm.extract(text)
        if suggestion is None:
            return draft
        return adopt_llm_suggestion(draft, suggestion, self._dictionary)


def adopt_llm_suggestion(
    draft: IntentDraft, suggestion: LlmSuggestion, dictionary: MasterDictionary
) -> IntentDraft:
    adopted = draft
    used = False
    if suggestion.region_name:
        entries = dictionary.regions_named(suggestion.region_name)
        if entries:
            resolved = resolve_region(entries, suggestion.region_name, dictionary)
            adopted = IntentDraft(
                region_code=resolved.region_code,
                region_name=resolved.region_name,
                district_code=resolved.district_code or adopted.district_code,
                candidates=resolved.candidates,
                industry_id=adopted.industry_id,
                budget_krw=adopted.budget_krw,
            )
            used = True
    if adopted.industry_id is None and suggestion.industry_id in dictionary.industry_names:
        adopted = IntentDraft(**{**adopted.__dict__, "industry_id": suggestion.industry_id})
        used = True
    if adopted.budget_krw is None and suggestion.budget_krw:
        adopted = IntentDraft(**{**adopted.__dict__, "budget_krw": int(suggestion.budget_krw)})
        used = True
    return IntentDraft(**{**adopted.__dict__, "llm_used": used}) if used else adopted


class IntentInteractor(IntentUseCase):
    def __init__(
        self,
        masters: MasterDictionaryPort,
        facts: ProfileFactsPort,
        llm: IntentLlmPort,
    ) -> None:
        self._masters = masters
        self._facts = facts
        self._llm = llm

    def myself(self) -> IntentResultDto:
        return IntentResultDto(
            intent_type="A",
            region_code="myself",
            region_name="배선동",
            district_code="00000",
            industry_id="cafe",
            budget_krw=1,
            missing=[],
            diagnosis=DiagnosisDto(
                type_code="mixed",
                type_name="혼합형",
                time_label="flat",
                peak_sales_band="11_14",
                sentence="배선 검증용 하드코딩 문장입니다.",
                year_quarter="20262",
                hour_gap_quarter="20254",
            ),
        )

    def parse(self, text: str) -> IntentResultDto:
        if not text or not text.strip():
            raise IntentTextEmptyError()
        dictionary = self._masters.load()
        draft = run_extractors(
            [
                RegionExtractor(dictionary),
                IndustryExtractor(dictionary),
                BudgetExtractor(),
                LlmFallbackExtractor(self._llm, dictionary),
            ],
            text,
        )
        return self._to_result(draft, dictionary)

    def diagnose(self, region_code: str, industry_id: str) -> IntentResultDto:
        dictionary = self._masters.load()
        entry = dictionary.region_by_code(region_code)
        if entry is None:
            raise RegionNotFoundError(region_code)
        if industry_id not in dictionary.industry_names:
            raise IndustryNotFoundError(industry_id)
        draft = IntentDraft(industry_id=industry_id).with_region(entry)
        return self._to_result(draft, dictionary)

    def _to_result(self, draft: IntentDraft, dictionary: MasterDictionary) -> IntentResultDto:
        diagnosis = (
            self._diagnose(draft, dictionary) if draft.intent_type == "A" else None
        )
        return IntentResultDto(
            intent_type=draft.intent_type,
            region_code=draft.region_code,
            region_name=draft.region_name,
            district_code=draft.district_code,
            industry_id=draft.industry_id,
            budget_krw=draft.budget_krw,
            missing=draft.missing,
            candidates=[
                RegionCandidateDto(c.region_code, c.name, c.district_code, c.district_name)
                for c in draft.candidates
            ],
            diagnosis=diagnosis,
            source="llm" if draft.llm_used else "rule",
        )

    def _diagnose(self, draft: IntentDraft, dictionary: MasterDictionary) -> DiagnosisDto | None:
        assert draft.region_code and draft.region_name and draft.industry_id
        profile = self._facts.latest_profile(draft.region_code, draft.region_name)
        if profile is None:
            return None  # 파생 배치 전이거나 원천에만 있는 옛 행정동
        peak = self._facts.peak_sales_band(draft.region_code, draft.industry_id)
        composed: Diagnosis = compose_diagnosis(
            profile, dictionary.industry_names[draft.industry_id], peak
        )
        return DiagnosisDto(**composed.__dict__)
