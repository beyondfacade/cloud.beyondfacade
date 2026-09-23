"""추출기 체인 — Chain of Responsibility (CLAUDE.md §5). if/elif가 아니라 리스트를 순회한다.

각 추출기는 자기 몫(동·업종·예산)만 채우고 초안을 다음으로 넘긴다. 사전은 생성자로 주입돼
도메인이 DB를 모른다. 규칙이 먼저고 LLM은 app 계층의 마지막 추출기다(포트가 필요해서).
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.intent.domain.value_objects.industry_synonyms import INDUSTRY_SYNONYMS
from apps.intent.domain.value_objects.intent_draft import IntentDraft
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary, RegionEntry


class IntentExtractor(ABC):
    @abstractmethod
    def extract(self, draft: IntentDraft, text: str) -> IntentDraft:
        """채울 수 있는 만큼 채운 새 초안을 돌려준다. 못 채우면 그대로 넘긴다."""


def run_extractors(extractors: Sequence[IntentExtractor], text: str) -> IntentDraft:
    draft = IntentDraft()
    for extractor in extractors:
        draft = extractor.extract(draft, text)
    return draft


def resolve_region(
    entries: Sequence[RegionEntry], text: str, dictionary: MasterDictionary
) -> IntentDraft | None:
    """같은 이름의 동이 여럿이면 텍스트의 구 이름으로 좁힌다. 못 좁히면 후보로 남긴다."""
    if len(entries) == 1:
        return IntentDraft().with_region(entries[0])
    mentioned = [
        code for name, code in dictionary.districts.items() if name in text
    ]
    narrowed = [e for e in entries if e.district_code in mentioned]
    if len(narrowed) == 1:
        return IntentDraft().with_region(narrowed[0])
    # 후보가 한 구 안에 있으면(역삼1동·역삼2동) 구는 확정할 수 있다
    districts = {e.district_code for e in entries}
    return IntentDraft(
        candidates=tuple(entries),
        district_code=next(iter(districts)) if len(districts) == 1 else None,
    )


class RegionExtractor(IntentExtractor):
    """동 이름(정확·기본) 우선, 그다음 구 이름. 긴 이름이 먼저 맞는다 — 부분 문자열 오매칭 방지."""

    def __init__(self, dictionary: MasterDictionary) -> None:
        self._dictionary = dictionary

    def extract(self, draft: IntentDraft, text: str) -> IntentDraft:
        for name in self._dictionary.region_names_longest_first():
            if name in text:
                resolved = resolve_region(self._dictionary.regions_named(name), text, self._dictionary)
                return IntentDraft(
                    region_code=resolved.region_code,
                    region_name=resolved.region_name,
                    district_code=resolved.district_code,
                    candidates=resolved.candidates,
                    industry_id=draft.industry_id,
                    budget_krw=draft.budget_krw,
                )
        for name in self._dictionary.district_names_longest_first():
            if name in text:
                return IntentDraft(
                    district_code=self._dictionary.districts[name],
                    industry_id=draft.industry_id,
                    budget_krw=draft.budget_krw,
                )
        return draft


class IndustryExtractor(IntentExtractor):
    def __init__(self, dictionary: MasterDictionary) -> None:
        # 마스터에 없는 업종으로는 절대 매칭되지 않는다
        self._synonyms = sorted(
            ((word, slug) for word, slug in INDUSTRY_SYNONYMS.items() if slug in dictionary.industry_names),
            key=lambda item: len(item[0]),
            reverse=True,
        )

    def extract(self, draft: IntentDraft, text: str) -> IntentDraft:
        lowered = text.lower()
        for word, slug in self._synonyms:
            if word.lower() in lowered:
                return IntentDraft(**{**draft.__dict__, "industry_id": slug})
        return draft


_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(억|천만|천|만)")  # 단위 없는 맨숫자(2층 등)는 금액 아님
_SCALE = {"억": 100_000_000, "천만": 10_000_000, "천": 10_000_000, "만": 10_000}


def parse_budget(text: str) -> int | None:
    """단위 붙은 첫 금액부터, 공백만 사이에 두고 이어지는 더 작은 단위를 합산한다 (1억 5천 → 1.5억)."""
    cleaned = text.replace(",", "")
    total, prev_end, prev_scale = None, 0, 0
    for match in _AMOUNT.finditer(cleaned):
        scale = _SCALE[match.group(2)]
        if total is not None and (cleaned[prev_end : match.start()].strip() or scale >= prev_scale):
            break
        total = (total or 0) + int(float(match.group(1)) * scale)
        prev_end, prev_scale = match.end(), scale
    return total


class BudgetExtractor(IntentExtractor):
    def extract(self, draft: IntentDraft, text: str) -> IntentDraft:
        budget = parse_budget(text)
        return draft if budget is None else IntentDraft(**{**draft.__dict__, "budget_krw": budget})
