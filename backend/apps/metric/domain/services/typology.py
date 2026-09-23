"""동네 유형 판정 — 결정 목록 (Chain of Responsibility, CLAUDE.md §5).

`if/elif` 체인이 아니라 규칙 객체 리스트다. 각 규칙이 자기 판정과 근거 문장을 함께 반환하고
첫 일치가 이긴다. 순서에 뜻이 있다 — 업무 밀집형이 앞에 있어야 명동·종로가 대학가형으로 새지
않고, 대학가형이 먹자형보다 앞이어야 건대입구·신촌이 먹자형으로 새지 않는다 (분류 문서 §4-1).

임계값은 전부 해당 분기 창의 분포에서 매 배치 재계산한다. 하드코딩 금지 — 절대값으로 굳히면
"서울 안에서의 상대 위치"라는 뜻이 사라진다.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from apps.metric.domain.services.quantiles import quantile


@dataclass(frozen=True)
class TypologyInput:
    """판정 입력 — 최근 4분기로 평활된 동 하나의 지표 (설계서 §5-2)."""

    worker_resident_ratio: float | None  # 직장 ÷ 상주. 직장인구 결측 11개 동은 None
    weekend_index: float | None  # 주말 일평균 ÷ 평일 일평균
    night_index: float | None  # 00_06 시간강도
    footfall_20s_share: float | None
    fnb_share: float | None  # (음식 + 유흥) ÷ 지출 총금액
    fnb_amount_per_resident: float | None  # fnb_share × 지출 총금액 ÷ 상주인구
    facility_total: int | None
    resident_total: int | None
    university_count: int


@dataclass(frozen=True)
class TypologyThresholds:
    worker_resident_q90: float | None
    weekend_q50: float | None
    university_median_positive: float | None
    footfall_20s_q90: float | None
    fnb_per_resident_q75: float | None
    fnb_share_q50: float | None
    fnb_share_q75: float | None
    night_q25: float | None
    night_q50: float | None
    facility_q75: float | None
    resident_floor: float | None  # 서울 하위 1% — 재건축 이주 동 방어 (설계서 §3-3)


@dataclass(frozen=True)
class TypologyVerdict:
    type_code: str
    reason: str


def derive_thresholds(inputs: Sequence[TypologyInput]) -> TypologyThresholds:
    """창의 분포에서 임계값을 다시 낸다. 직장인구 결측 동은 직장비 분포에서 뺀다 (설계서 §3-4)."""

    def present(attribute: str) -> list[float]:
        """결측은 분포에서 뺀다 — 0으로 채우면 임계값이 통째로 내려앉는다 (설계서 §3-4)."""
        return [
            float(value)
            for i in inputs
            if (value := getattr(i, attribute)) is not None
        ]

    universities = [float(i.university_count) for i in inputs if i.university_count > 0]
    night = present("night_index")
    return TypologyThresholds(
        worker_resident_q90=quantile(present("worker_resident_ratio"), 0.90),
        weekend_q50=quantile(present("weekend_index"), 0.50),
        university_median_positive=quantile(universities, 0.50),
        footfall_20s_q90=quantile(present("footfall_20s_share"), 0.90),
        fnb_per_resident_q75=quantile(present("fnb_amount_per_resident"), 0.75),
        fnb_share_q50=quantile(present("fnb_share"), 0.50),
        fnb_share_q75=quantile(present("fnb_share"), 0.75),
        night_q25=quantile(night, 0.25),
        night_q50=quantile(night, 0.50),
        facility_q75=quantile(present("facility_total"), 0.75),
        resident_floor=quantile(present("resident_total"), 0.01),
    )


def _at_least(value: float | None, threshold: float | None) -> bool:
    """값이나 임계값이 없으면 규칙은 통과하지 않는다 — 결측을 0으로 읽지 않기 위해서다."""
    return value is not None and threshold is not None and value >= threshold


def _below(value: float | None, threshold: float | None) -> bool:
    return value is not None and threshold is not None and value < threshold


def _as_float(value: float | int | None) -> float | None:
    return None if value is None else float(value)


class TypologyRule(ABC):
    @abstractmethod
    def judge(
        self, metrics: TypologyInput, thresholds: TypologyThresholds
    ) -> TypologyVerdict | None:
        """판정되면 Verdict, 아니면 None을 반환해 다음 규칙에 넘긴다."""


class ResidentFloorRule(TypologyRule):
    """R0 — 상주인구가 서울 하위 1%인 동은 비율 기반 판정에서 제외한다 (설계서 §3-3).

    반포본동은 상주 117명이라 직장÷상주가 48.5로 업무 밀집형에 걸린다. 재건축 이주로 분모가
    비정상인 것이지 도심이어서가 아니다.
    """

    def judge(self, metrics, thresholds):
        if not _below(_as_float(metrics.resident_total), thresholds.resident_floor):
            return None
        return TypologyVerdict(
            type_code="mixed",
            reason="상주인구가 비정상적으로 적어(재건축 등) 비율 판정을 적용하지 않았습니다.",
        )


class OfficeRule(TypologyRule):
    """R1 — 직장비 상위 10% AND 주말 유동이 중앙값 미만. 직장인구 결측 동은 통과할 수 없다."""

    def judge(self, metrics, thresholds):
        if not _at_least(metrics.worker_resident_ratio, thresholds.worker_resident_q90):
            return None
        if not _below(metrics.weekend_index, thresholds.weekend_q50):
            return None
        return TypologyVerdict(
            type_code="office",
            reason=(
                f"직장인구가 상주인구의 {metrics.worker_resident_ratio:.1f}배로 서울 상위 10%이고, "
                "주말 유동이 평일보다 적습니다."
            ),
        )


class CampusRule(TypologyRule):
    """R2 — 대학 시설 수가 (대학이 있는 동의) 중앙값 이상 AND 유동 20대 비중 상위 10%."""

    def judge(self, metrics, thresholds):
        if not _at_least(float(metrics.university_count), thresholds.university_median_positive):
            return None
        if not _at_least(metrics.footfall_20s_share, thresholds.footfall_20s_q90):
            return None
        return TypologyVerdict(
            type_code="campus",
            reason=(
                f"대학 시설이 있고, 거리 위 20대 비중이 {metrics.footfall_20s_share * 100:.1f}%로 "
                "서울 상위 10%입니다."
            ),
        )


class DiningRule(TypologyRule):
    """R3 — A(1인당 결제액 상위 25% AND 비중 중앙값 이상) 또는 B(비중 상위 25% AND 심야 체류 하위 25%)."""

    def judge(self, metrics, thresholds):
        if _at_least(metrics.fnb_amount_per_resident, thresholds.fnb_per_resident_q75) and (
            _at_least(metrics.fnb_share, thresholds.fnb_share_q50)
        ):
            return TypologyVerdict(
                type_code="dining",
                reason=(
                    "이 동에서 결제된 음식·유흥 금액이 상주인구 1인당 "
                    f"{round(metrics.fnb_amount_per_resident):,}원으로 서울 상위 25%입니다."
                ),
            )
        if _at_least(metrics.fnb_share, thresholds.fnb_share_q75) and _below(
            metrics.night_index, thresholds.night_q25
        ):
            return TypologyVerdict(
                type_code="dining",
                reason=(
                    f"결제액의 {metrics.fnb_share * 100:.1f}%가 음식·유흥이고, "
                    "낮 시간 유동이 서울 상위 25%입니다."
                ),
            )
        return None


class HubRule(TypologyRule):
    """R4 — 집객시설 상위 25% AND 심야 체류가 중앙값 미만(=낮이 밤보다 강하다)."""

    def judge(self, metrics, thresholds):
        if not _at_least(_as_float(metrics.facility_total), thresholds.facility_q75):
            return None
        if not _below(metrics.night_index, thresholds.night_q50):
            return None
        return TypologyVerdict(
            type_code="hub",
            reason=(
                f"집객시설이 {metrics.facility_total}개로 서울 상위 25%이고, "
                "낮 시간 유동이 밤보다 강합니다."
            ),
        )


class ResidentialRule(TypologyRule):
    """R5 — (직장비 < 1.0 또는 직장인구 결측) AND 심야 체류가 하위 25%에 들지 않는다."""

    def judge(self, metrics, thresholds):
        ratio = metrics.worker_resident_ratio
        if ratio is not None and ratio >= 1.0:
            return None
        if not _at_least(metrics.night_index, thresholds.night_q25):
            return None
        tail = "밤 시간 체류가 서울 하위 25%에 들지 않습니다."
        # 직장인구 결측 동은 0으로 채우면 주거형으로 오판하므로 근거에서 앞 절을 뺀다 (설계서 §3-4)
        reason = tail if ratio is None else f"직장인구가 상주인구보다 적고, {tail}"
        return TypologyVerdict(type_code="residential", reason=reason)


class MixedRule(TypologyRule):
    """R6 — 최후의 보루."""

    def judge(self, metrics, thresholds):
        return TypologyVerdict(
            type_code="mixed",
            reason="어느 축에서도 서울 상위·하위 경계를 넘지 않습니다.",
        )


_RULES: tuple[TypologyRule, ...] = (
    ResidentFloorRule(),
    OfficeRule(),
    CampusRule(),
    DiningRule(),
    HubRule(),
    ResidentialRule(),
    MixedRule(),
)


def classify(metrics: TypologyInput, thresholds: TypologyThresholds) -> TypologyVerdict:
    """결정 목록을 순서대로 훑어 첫 일치를 반환한다."""
    for rule in _RULES:
        verdict = rule.judge(metrics, thresholds)
        if verdict is not None:
            return verdict
    raise AssertionError("MixedRule이 항상 판정하므로 도달할 수 없다")
