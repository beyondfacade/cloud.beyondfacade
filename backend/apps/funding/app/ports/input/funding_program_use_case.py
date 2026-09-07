"""Driving Port — funding_program UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date

from apps.funding.app.dtos.funding_program_dto import FundingProgramDto


class FundingProgramUseCase(ABC):
    @abstractmethod
    def myself(self) -> FundingProgramDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def ingest(self) -> tuple[int, int]:
        """전량 수집·업서트(멱등) — (신규, 갱신) 건수를 반환한다."""

    @abstractmethod
    def refresh_expirations(self, today: date) -> int:
        """마감일 지난 공고 is_expired 갱신(연장 시 복원 포함) — 신규 만료 건수 반환."""

    @abstractmethod
    def list_open(self, limit: int) -> list[FundingProgramDto]:
        """미만료 공고를 마감 임박순(마감일 오름차순, 상시는 뒤)으로 반환한다."""
