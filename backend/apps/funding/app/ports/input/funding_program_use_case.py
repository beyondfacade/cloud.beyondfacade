"""Driving Port — funding_program UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date

from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateListDto,
    FundingProgramDto,
)


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

    @abstractmethod
    def list_candidates(
        self,
        industry_id: str | None,
        external_funding_need: int | None,
        stage: str | None,
    ) -> FundingCandidateListDto:
        """서울 창업자에게 해당하는 미만료 공고 상위 8건 — 결정론 필터 (설계서 §3).

        자격 확정이 아니다. `industry_id`·`external_funding_need`는 되돌려주기만 한다.
        """
