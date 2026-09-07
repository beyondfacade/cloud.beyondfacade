from dataclasses import asdict
from datetime import date

from apps.funding.app.dtos.funding_program_dto import FundingProgramDto
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.app.ports.output.funding_program_port import (
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram


def _to_dto(entity: FundingProgram) -> FundingProgramDto:
    fields = asdict(entity)
    fields.pop("posted_at")
    fields.pop("source_updated_at")
    return FundingProgramDto(**fields)


class FundingProgramInteractor(FundingProgramUseCase):
    def __init__(
        self,
        repository: FundingProgramRepositoryPort,
        gateway: FundingSearchGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def myself(self) -> FundingProgramDto:
        return FundingProgramDto(
            program_id="myself",
            source="bizinfo",
            title="funding BC 배선 검증",
            org="beyondfacade",
            url="https://example.com/myself",
            apply_period="2026-09-07 ~ 2026-09-07",
        )

    def ingest(self) -> tuple[int, int]:
        return self._repository.upsert(self._gateway.fetch_all())

    def refresh_expirations(self, today: date) -> int:
        return self._repository.refresh_expirations(today)

    def list_open(self, limit: int) -> list[FundingProgramDto]:
        return [_to_dto(program) for program in self._repository.list_open(limit)]
