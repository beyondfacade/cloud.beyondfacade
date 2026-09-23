"""Driving Port — region_profile UseCase 인터페이스 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_profile_dto import (
    ProfileMetricValueDto,
    ProfileTypeDto,
    RegionProfileDto,
)


class RegionProfileUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionProfileDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, quarters: list[str]) -> int:
        """분기 목록의 동네 프로필을 재계산·업서트하고 처리 건수를 반환한다 (멱등).

        각 분기는 그 분기를 포함한 직전 4분기 창으로 판정한다. 임계값은 창마다 다시 낸다.
        """

    @abstractmethod
    def list_metric_values(
        self, metric: str, year_quarter: str | None
    ) -> list[ProfileMetricValueDto]:
        """단계구분도용 — 해당 분기의 행정동별 지표값 (값 None 행 제외).

        분기를 생략하면 가장 최근 분기를 쓴다. 미지원 metric은 MetricNotFoundError.
        """

    @abstractmethod
    def list_types(self, year_quarter: str | None) -> list[ProfileTypeDto]:
        """유형 단계구분도용 — 해당 분기의 행정동별 유형 코드 (범주 계약, 숫자 계약과 경로 분리).

        분기를 생략하면 가장 최근 분기를 쓴다. 배치 전이면 빈 목록.
        """

    @abstractmethod
    def find(self, region_code: str, year_quarter: str) -> RegionProfileDto | None:
        """단건 조회 — 없으면 None (사이드패널 동네 프로필용)."""

    @abstractmethod
    def find_latest(self, region_code: str) -> RegionProfileDto | None:
        """그 동의 가장 최근 분기 — 없으면 None. 화면은 어느 분기가 최신인지 모른다."""
