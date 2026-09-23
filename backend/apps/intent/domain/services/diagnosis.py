"""한 줄 진단 — LLM이 아니라 어휘 테이블로 조립한다 (설계서 §6).

정점은 gap이 아니라 **매출 강도 최대 구간**이다. v0.26.0 검증에서 어긋남의 부호는 절대값이 아니라
상대 순위에 있음이 확인됐다 — "언제 돈이 도나"는 매출 강도로 답한다.
"""

from dataclasses import dataclass

from apps.intent.domain.value_objects.neighborhood_vocabulary import (
    hour_band_name,
    type_name,
)


@dataclass(frozen=True)
class ProfileFacts:
    region_name: str
    type_code: str
    type_reason: str
    time_label: str | None
    year_quarter: str


@dataclass(frozen=True)
class PeakSalesBand:
    hour_band: str
    year_quarter: str


@dataclass(frozen=True)
class Diagnosis:
    type_code: str
    type_name: str
    time_label: str | None
    peak_sales_band: str | None
    sentence: str
    year_quarter: str  # 프로필 기준 분기
    hour_gap_quarter: str | None  # 매출 정점 기준 분기 — 프로필보다 짧다(20254까지)


def topic_particle(word: str) -> str:
    """은/는 — 마지막 글자가 한글이고 받침이 있으면 은."""
    last = word[-1]
    if "가" <= last <= "힣" and (ord(last) - ord("가")) % 28:
        return "은"
    return "는"


def compose_diagnosis(
    profile: ProfileFacts, industry_name: str, peak: PeakSalesBand | None
) -> Diagnosis:
    subject = f"{profile.region_name}{topic_particle(profile.region_name)}"
    name = type_name(profile.type_code) or profile.type_code

    # 상주인구 하한(재건축 등)에 걸린 동 — 억지로 유형을 붙이지 않고 근거 문장을 그대로 쓴다
    if "재건축" in profile.type_reason:
        return Diagnosis(
            type_code=profile.type_code,
            type_name=name,
            time_label=profile.time_label,
            peak_sales_band=None,
            sentence=f"{subject} {profile.type_reason}",
            year_quarter=profile.year_quarter,
            hour_gap_quarter=None,
        )

    head = f"{subject} 뚜렷한 특징이 없는 혼합형" if profile.type_code == "mixed" else f"{subject} {name}"
    if peak is None:
        sentence = f"{head}입니다."
    else:
        sentence = (
            f"{head}이고, {industry_name}{topic_particle(industry_name)} "
            f"{hour_band_name(peak.hour_band)}에 돈이 돕니다."
        )
    return Diagnosis(
        type_code=profile.type_code,
        type_name=name,
        time_label=profile.time_label,
        peak_sales_band=None if peak is None else peak.hour_band,
        sentence=sentence,
        year_quarter=profile.year_quarter,
        hour_gap_quarter=None if peak is None else peak.year_quarter,
    )
