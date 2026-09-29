"""Driven Ports — verdict가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
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
    def latest_contexts(self) -> list[RegionContext]:
        """전 행정동 1행씩 — 최신 분기 상주인구·상권변화지표·서울 베이스라인."""

    @abstractmethod
    def latest_store_counts(self) -> list[LatestStoreCount]:
        """region_industry_metric 최신 연도의 동×업종 점포수."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def judged_industries(self) -> list[JudgedIndustry]:
        """판정 대상 업종 — industry 마스터 − EXCLUDED_INDUSTRIES."""


class RegionCatalogPort(ABC):
    @abstractmethod
    def regions(self) -> list[RegionInfo]:
        """전 행정동 이름 + 최신 분기 동네 유형 (대안 업종 고정 축)."""
