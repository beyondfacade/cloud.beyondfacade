"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from functools import lru_cache

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import BizinfoGateway
from apps.funding.adapter.outbound.gateways.latest_rates_gateway import LatestRatesGateway
from apps.funding.adapter.outbound.gateways.rag_question_ranker_gateway import (
    RagQuestionRankerGateway,
)
from apps.funding.adapter.outbound.gateways.seoul_district_gateway import (
    SeoulDistrictNamesGateway,
)
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.adapter.outbound.repositories.funding_program_repository_proxy import (
    CachingFundingProgramRepositoryProxy,
)
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.app.ports.output.funding_program_port import FundingProgramRepositoryPort
from apps.funding.app.use_cases.funding_program_interactor import (
    FundingProgramInteractor,
)


@lru_cache
def _cached_repository() -> FundingProgramRepositoryPort:
    """캐싱 Proxy가 상태를 가지므로 프로세스당 1개 — API 라우터와 agent의 FundingFactsGateway가 공유한다.
    수집 CLI(`funding_collector`)는 쓰기 경로라 이 함수를 쓰지 않는다."""
    return CachingFundingProgramRepositoryProxy(SqlAlchemyFundingProgramRepository())


def get_funding_program_use_case() -> FundingProgramUseCase:
    districts = SeoulDistrictNamesGateway()
    return FundingProgramInteractor(
        repository=_cached_repository(),
        gateway=BizinfoGateway(),
        seoul_districts=districts,
        district_lookup=districts,
        rates=LatestRatesGateway(),
        ranker=RagQuestionRankerGateway(),
    )
