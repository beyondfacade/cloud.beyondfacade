"""인허가 원천 한 건의 업종(industry_id)을 정하는 분류기 — Strategy (CLAUDE.md §5).

인허가 슬러그 하나가 여러 업종을 담는 경우(일반음식점 → 한식·중식·…)가 생겨 "슬러그 = 업종" 가정이 깨졌다.
슬러그마다 전략 하나:
- 기존 6슬러그(휴게음식점·미용업·…)는 슬러그가 곧 업종 → FixedIndustryClassifier (동작 불변)
- general_restaurants 는 업태구분명(BZSTAT_SE_NM)으로 나눈다 → BusinessTypeClassifier

매핑표 근거: 강남구 파일럿 51,402건 업태 전수 분포 (설계서 2026-09-28-industry-expansion-design.md §2).
순수 파이썬 — 프레임워크 import 없음.
"""

import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Mapping


class PermitIndustryClassifier(ABC):
    @property
    @abstractmethod
    def industry_ids(self) -> frozenset[str]:
        """이 전략이 낼 수 있는 업종 전체 — 증분 커서·수집 대상 계산에 쓴다."""

    @abstractmethod
    def classify(self, business_type: str | None, name: str | None) -> str:
        """원천 한 건의 업태구분명·상호 → industry_id."""


class FixedIndustryClassifier(PermitIndustryClassifier):
    """슬러그가 곧 업종인 경우 — 무엇이 오든 앵커 업종."""

    def __init__(self, industry_id: str) -> None:
        self._industry_id = industry_id

    @property
    def industry_ids(self) -> frozenset[str]:
        return frozenset({self._industry_id})

    def classify(self, business_type: str | None, name: str | None) -> str:
        return self._industry_id


def _normalize(text: str | None) -> str:
    return unicodedata.normalize("NFC", (text or "")).replace(" ", "").strip()


class BusinessTypeClassifier(PermitIndustryClassifier):
    """업태구분명 → 업종. 표에 없는 업태와 제외 표식(예: 한시적 영업)은 fallback 업종."""

    def __init__(
        self,
        mapping: Mapping[str, str],
        fallback: str,
        excluded_name_markers: tuple[str, ...] = (),
    ) -> None:
        self._mapping = {_normalize(k): v for k, v in mapping.items()}
        self._fallback = fallback
        self._markers = excluded_name_markers

    @property
    def industry_ids(self) -> frozenset[str]:
        return frozenset(self._mapping.values()) | {self._fallback}

    def classify(self, business_type: str | None, name: str | None) -> str:
        if name and any(marker in name for marker in self._markers):
            return self._fallback
        return self._mapping.get(_normalize(business_type), self._fallback)


# 일반음식점 업태구분명 → 업종. 표에 없는 값(기타·패스트푸드·까페·전통찻집·뷔페식·출장조리·이동조리·
# 푸드트럭·키즈카페)은 restaurant_other — 판정 대상이 아니지만 폐업 마커·포화 분모로 쓰므로 버리지 않는다.
# '까페'는 주류·식사 허가를 받은 일반음식점이라 휴게음식점 원천의 cafe 와 모집단이 다르다 → 합치지 않는다.
GENERAL_RESTAURANT_BUSINESS_TYPES: dict[str, str] = {
    "한식": "korean_food",
    "식육(숯불구이)": "korean_food",
    "탕류(보신용)": "korean_food",
    "냉면집": "korean_food",
    "중국식": "chinese_food",
    "일식": "japanese_food",
    "횟집": "japanese_food",
    "복어취급": "japanese_food",
    "경양식": "western_food",
    "패밀리레스트랑": "western_food",
    "외국음식전문점(인도,태국등)": "western_food",
    "분식": "snack",
    "김밥(도시락)": "snack",
    "통닭(치킨)": "chicken",
    "호프/통닭": "pub",
    "정종/대포집/소주방": "pub",
    "감성주점": "pub",
    "라이브카페": "pub",
}

RESTAURANT_OTHER = "restaurant_other"

# 상호에 "(한시적)"이 붙은 건은 팝업·행사 영업이라 어떤 업태든 판정 대상에서 뺀다 (파일럿 '기타' 표본 근거)
GENERAL_RESTAURANT_CLASSIFIER = BusinessTypeClassifier(
    GENERAL_RESTAURANT_BUSINESS_TYPES,
    fallback=RESTAURANT_OTHER,
    excluded_name_markers=("(한시적)",),
)

# 슬러그 → 전략. 여기 없는 슬러그는 FixedIndustryClassifier(앵커 업종).
PERMIT_CLASSIFIERS: dict[str, PermitIndustryClassifier] = {
    "general_restaurants": GENERAL_RESTAURANT_CLASSIFIER,
}

# 슬러그 → store_id 접두. 업종이 수집 후 재분류될 수 있는 슬러그는 업종이 아니라 슬러그 기반 접두를 써야
# 같은 관리번호가 같은 행으로 업서트된다. 없는 슬러그는 앵커 업종(기존 행 접두와 동일).
PERMIT_STORE_PREFIXES: dict[str, str] = {
    "general_restaurants": "restaurant",
}


def permit_classifier_for(slug: str, anchor_industry_id: str) -> PermitIndustryClassifier:
    return PERMIT_CLASSIFIERS.get(slug) or FixedIndustryClassifier(anchor_industry_id)
