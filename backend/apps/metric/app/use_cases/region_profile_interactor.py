"""동네 프로필 배치 — 원자료를 4분기 창으로 평활해 유형과 시간대 라벨을 낸다 (설계서 §5)."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict

from apps.metric.app.dtos.region_profile_dto import (
    RegionProfileDto,
    RegionQuarterObservation,
)
from apps.metric.app.ports.input.region_profile_use_case import RegionProfileUseCase
from apps.metric.app.ports.output.region_profile_port import (
    NeighborhoodObservationPort,
    RegionProfileRepositoryPort,
)
from apps.metric.domain.entities.region_profile_entity import RegionProfile
from apps.metric.domain.services.time_label import (
    TimeLabelInput,
    derive_flatness_threshold,
    label_time,
)
from apps.metric.domain.services.typology import (
    TypologyInput,
    classify,
    derive_thresholds,
)
from apps.metric.domain.value_objects.hour_band import HOUR_BANDS, band_intensities
from apps.metric.domain.value_objects.year_quarter import quarter_window

_WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri")
_WEEKEND: tuple[str, ...] = ("sat", "sun")

# 분기 단독 판정은 불변 동이 75.1%인데 4분기 이동평균은 81.6%다 (분류 문서 §5-1)
_WINDOW_SIZE = 4


def _mean(values: Sequence[float | int | None]) -> float | None:
    """결측을 0으로 읽지 않는다 — 있는 분기만 평균한다."""
    present = [float(value) for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _mean_by_key(
    maps: Sequence[Mapping[str, float]], keys: Sequence[str]
) -> dict[str, float]:
    return {key: _mean([m.get(key) for m in maps]) or 0.0 for key in keys}


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


class _Smoothed:
    """창 안의 관측을 평균한 한 동의 상태 — 판정과 저장이 같은 수치를 본다."""

    def __init__(self, observations: Sequence[RegionQuarterObservation]) -> None:
        self.worker_total = _mean([o.worker_total for o in observations])
        self.resident_total = _mean([o.resident_total for o in observations])
        self.facility_total = _mean([o.facility_total for o in observations])
        self.university_count = _mean([o.university_count for o in observations]) or 0.0
        self.spending_total = _mean([o.spending_total for o in observations])
        self.spending_fnb = _mean([o.spending_fnb for o in observations])
        self.hours = _mean_by_key([o.footfall_by_hour for o in observations], HOUR_BANDS)
        dow = _mean_by_key(
            [o.footfall_by_dow for o in observations], (*_WEEKDAYS, *_WEEKEND)
        )
        self.weekend_index = _ratio(
            sum(dow[day] for day in _WEEKEND) / len(_WEEKEND),
            sum(dow[day] for day in _WEEKDAYS) / len(_WEEKDAYS),
        )
        self.night_index = band_intensities(self.hours).get("00_06")
        self.footfall_20s_share = _ratio(
            _mean([o.footfall_20s for o in observations]),
            _mean([o.footfall_age_total for o in observations]),
        )
        self.fnb_share = _ratio(self.spending_fnb, self.spending_total)

    def to_typology_input(self) -> TypologyInput:
        return TypologyInput(
            worker_resident_ratio=_ratio(self.worker_total, self.resident_total),
            weekend_index=self.weekend_index,
            night_index=self.night_index,
            footfall_20s_share=self.footfall_20s_share,
            fnb_share=self.fnb_share,
            # fnb_share × 지출 총금액 ÷ 상주인구 — 약분하면 음식·유흥 금액 ÷ 상주인구다
            fnb_amount_per_resident=_ratio(self.spending_fnb, self.resident_total),
            facility_total=None if self.facility_total is None else round(self.facility_total),
            resident_total=None if self.resident_total is None else round(self.resident_total),
            university_count=round(self.university_count),
        )

    def to_time_label_input(self) -> TimeLabelInput:
        return TimeLabelInput(hour_values=self.hours)


def _to_dto(entity: RegionProfile | None) -> RegionProfileDto | None:
    return None if entity is None else RegionProfileDto(**asdict(entity))


class RegionProfileInteractor(RegionProfileUseCase):
    def __init__(
        self,
        repository: RegionProfileRepositoryPort,
        observations: NeighborhoodObservationPort,
        window_size: int = _WINDOW_SIZE,
    ) -> None:
        self._repository = repository
        self._observations = observations
        self._window_size = window_size

    def myself(self) -> RegionProfileDto:
        return RegionProfileDto(
            region_code="myself",
            year_quarter="20261",
            neighborhood_type="mixed",
            type_reason="배선 검증용 하드코딩 값입니다.",
            time_label="flat",
            peak_block="day",
            trough_block="night",
            worker_resident_ratio=1.0,
            weekend_index=1.0,
            night_index=1.0,
            footfall_20s_share=0.12,
            fnb_share=0.22,
            facility_total=1,
            resident_total=1,
        )

    def build(self, quarters: list[str]) -> int:
        windows = {target: quarter_window(target, self._window_size) for target in quarters}
        needed = sorted({quarter for window in windows.values() for quarter in window})
        by_quarter: dict[str, dict[str, RegionQuarterObservation]] = defaultdict(dict)
        for observation in self._observations.quarter_observations(needed):
            by_quarter[observation.year_quarter][observation.region_code] = observation

        profiles: list[RegionProfile] = []
        for target in sorted(quarters):
            profiles.extend(self._profiles_for(target, windows[target], by_quarter))
        return self._repository.upsert(profiles)

    def _profiles_for(
        self,
        target: str,
        window: Sequence[str],
        by_quarter: Mapping[str, Mapping[str, RegionQuarterObservation]],
    ) -> list[RegionProfile]:
        present = by_quarter.get(target, {})
        if not present:
            return []
        smoothed = {
            region_code: _Smoothed(
                [
                    by_quarter[quarter][region_code]
                    for quarter in window
                    if region_code in by_quarter.get(quarter, {})
                ]
            )
            for region_code in present
        }
        typology_inputs = {code: s.to_typology_input() for code, s in smoothed.items()}
        label_inputs = {code: s.to_time_label_input() for code, s in smoothed.items()}
        # 임계값은 이 창의 분포에서 매번 다시 낸다 — 하드코딩 금지 (설계서 §3)
        thresholds = derive_thresholds(list(typology_inputs.values()))
        flatness_threshold = derive_flatness_threshold(list(label_inputs.values()))
        return [
            self._profile(
                region_code,
                target,
                typology_inputs[region_code],
                label_inputs[region_code],
                thresholds,
                flatness_threshold,
            )
            for region_code in sorted(present)
        ]

    @staticmethod
    def _profile(
        region_code, target, typology_input, label_input, thresholds, flatness_threshold
    ) -> RegionProfile:
        verdict = classify(typology_input, thresholds)
        label = label_time(label_input, flatness_threshold)
        return RegionProfile(
            region_code=region_code,
            year_quarter=target,
            neighborhood_type=verdict.type_code,
            type_reason=verdict.reason,
            time_label=label.time_label,
            peak_block=label.peak_block,
            trough_block=label.trough_block,
            worker_resident_ratio=typology_input.worker_resident_ratio,
            weekend_index=typology_input.weekend_index,
            night_index=typology_input.night_index,
            footfall_20s_share=typology_input.footfall_20s_share,
            fnb_share=typology_input.fnb_share,
            facility_total=typology_input.facility_total,
            resident_total=typology_input.resident_total,
        )

    def find(self, region_code: str, year_quarter: str) -> RegionProfileDto | None:
        return _to_dto(self._repository.find(region_code, year_quarter))

    def find_latest(self, region_code: str) -> RegionProfileDto | None:
        return _to_dto(self._repository.find_latest(region_code))
