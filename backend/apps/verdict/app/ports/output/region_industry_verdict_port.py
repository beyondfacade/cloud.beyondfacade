"""Driven Ports — verdict가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    EntrantOutcome,
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    RegionInfo,
    StoreSignalStat,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict


class RegionIndustryVerdictRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, verdicts: list[RegionIndustryVerdict]) -> int:
        """(region_code, industry_id) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def list_by_industry(self, industry_id: str) -> list[RegionIndustryVerdict]:
        """해당 업종의 전 행정동 판정을 region_code 순으로."""

    @abstractmethod
    def list_by_region(self, region_code: str) -> list[RegionIndustryVerdict]:
        """해당 동의 전 업종 판정을 industry_id 순으로 (대안 동네 고정 축)."""

    @abstractmethod
    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdict | None:
        """복합키 단건 — 없으면 None."""

    @abstractmethod
    def delete_other_industries(self, keep_industry_ids: Iterable[str]) -> int:
        """판정 대상에서 빠진 업종의 행을 지운다(배치 prune) — 삭제 건수 반환."""


class StoreSignalStatsPort(ABC):
    @abstractmethod
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """store 원천에서 동×업종별 12개월 개폐업·3년 코호트·최근 3년 폐업 중위개월 (region_code 보유분만)."""


class RegionContextPort(ABC):
    @abstractmethod
    def latest_contexts(self, quarter_max: str | None = None) -> list[RegionContext]:
        """전 행정동 1행씩 — 최신 분기 상주인구·상권변화지표·서울 베이스라인. quarter_max('20221')를 주면 그 분기까지의 최신 (백테스트)."""

    @abstractmethod
    def latest_store_counts(self, year_max: int | None = None) -> list[LatestStoreCount]:
        """region_industry_metric 최신 연도의 동×업종 점포수. year_max를 주면 그 연도까지의 최신 (백테스트)."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def judged_industries(self) -> list[JudgedIndustry]:
        """판정 대상 업종 — industry 마스터 − EXCLUDED_INDUSTRIES."""

    @abstractmethod
    def named_industries(self, industry_ids: Iterable[str]) -> list[JudgedIndustry]:
        """제외 여부와 무관하게 주어진 업종의 이름 — 재포함 심사 백테스트용 (업종 특화 신호 설계서 §8)."""


class RegionCatalogPort(ABC):
    @abstractmethod
    def regions(self) -> list[RegionInfo]:
        """전 행정동 이름 + 최신 분기 동네 유형 (대안 업종 고정 축)."""


class EntrantOutcomePort(ABC):
    @abstractmethod
    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        """백테스트 라벨 — [as_of, as_of+entry_days) 개업 점포 중 개업 후 horizon_days 안에 폐업한 수 (동×업종)."""


class IndustrySignalDataPort(ABC):
    """한 업종군의 개폐업 원천 — 창 집계·점포수·진입 결과가 같은 원천에서 함께 나온다(원천을 바꾸면 셋이 같이 바뀐다,
    업종 특화 신호 설계서 §4). 인허가 원천은 PermitSignalData가 기존 포트 3개를 묶어 이 모양으로 만든다."""

    @abstractmethod
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """동×업종별 12개월 개폐업·코호트·최근 3년 폐업(원천이 못 주는 항목은 0/None)."""

    @abstractmethod
    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """포화 분자 — 동×업종 점포수. 상한이 None이면 최신 (백테스트는 상한을 준다)."""

    @abstractmethod
    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        """백테스트 결과 라벨 — 진입 코호트, 또는 집계 원천이면 재고 결과(설계서 §7-3)."""
