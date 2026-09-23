"""Driven Ports — intent가 바깥 세계에 요구하는 계약 셋 (ISP). 전부 읽기다 — 이 BC는 쓰지 않는다."""

from abc import ABC, abstractmethod

from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.domain.services.diagnosis import PeakSalesBand, ProfileFacts
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary


class MasterDictionaryPort(ABC):
    @abstractmethod
    def load(self) -> MasterDictionary:
        """동·구·업종 마스터. 캐싱은 어댑터 몫이다."""


class ProfileFactsPort(ABC):
    @abstractmethod
    def latest_profile(self, region_code: str, region_name: str) -> ProfileFacts | None:
        """그 동의 최신 분기 프로필 — 없으면 None."""

    @abstractmethod
    def peak_sales_band(self, region_code: str, industry_id: str) -> PeakSalesBand | None:
        """그 동·업종의 최신 분기에서 매출 강도가 가장 큰 시간 구간 — 매출 행이 없으면 None."""


class IntentLlmPort(ABC):
    @abstractmethod
    def extract(self, text: str) -> LlmSuggestion | None:
        """자유문에서 동 이름·업종·예산을 뽑는다. 타임아웃·오류·키 없음은 전부 None — 관문이 죽지 않는다."""
