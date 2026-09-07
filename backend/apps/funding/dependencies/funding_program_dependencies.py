"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import BizinfoGateway
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.app.use_cases.funding_program_interactor import (
    FundingProgramInteractor,
)


def get_funding_program_use_case() -> FundingProgramUseCase:
    return FundingProgramInteractor(
        repository=SqlAlchemyFundingProgramRepository(),
        gateway=BizinfoGateway(),
    )
