"""Driven Port — 유사 사례 분석이 요구하는 서울 전체 업종별 월 개폐업 흐름."""

from abc import ABC, abstractmethod

from apps.shock.domain.services.industry_flows import IndustryFlows


class StoreFlowPort(ABC):
    @abstractmethod
    def monthly_flows(self) -> list[IndustryFlows]:
        """비교 가능한 업종마다 전 기간 월별 개업·폐업 수."""
