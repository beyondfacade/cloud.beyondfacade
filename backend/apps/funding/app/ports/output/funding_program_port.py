"""Driven Ports — funding_program이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.funding.domain.entities.funding_program_entity import FundingProgram


class FundingProgramRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, programs: list[FundingProgram]) -> tuple[int, int]:
        """program_id 기준 업서트(멱등) — (신규, 갱신) 건수 반환."""

    @abstractmethod
    def refresh_expirations(self, today: date) -> int:
        """deadline < today → is_expired=True, 연장된 공고는 복원 — 신규 만료 건수 반환."""

    @abstractmethod
    def list_open(self, limit: int) -> list[FundingProgram]:
        """미만료 공고 마감일 오름차순(상시=NULL은 뒤) limit건."""


class FundingSearchGatewayPort(ABC):
    @abstractmethod
    def fetch_all(self) -> list[FundingProgram]:
        """원천 API에서 전체 공고를 수신해 엔티티로 반환한다."""
