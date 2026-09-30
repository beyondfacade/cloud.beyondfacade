"""Driven Ports — 유사 사례 분석이 요구하는 서울 전체 업종별 월 개폐업 흐름과 최근 뉴스."""

from abc import ABC, abstractmethod

from apps.shock.domain.services.industry_flows import IndustryFlows
from apps.shock.domain.value_objects.news_headline import NewsHeadline


class StoreFlowPort(ABC):
    @abstractmethod
    def monthly_flows(self) -> list[IndustryFlows]:
        """비교 가능한 업종마다 전 기간 월별 개업·폐업 수."""


class RecentNewsPort(ABC):
    @abstractmethod
    def latest(self, keyword: str) -> list[NewsHeadline]:
        """단어로 찾은 최신 기사 헤드라인 (최신순)."""
