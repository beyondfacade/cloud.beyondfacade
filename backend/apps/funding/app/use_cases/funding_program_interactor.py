from dataclasses import asdict
from datetime import date

from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateDto,
    FundingCandidateListDto,
    FundingProgramDto,
    SupportGuideDto,
    SupportItemDto,
)
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.app.ports.output.funding_program_port import (
    DistrictNameLookupPort,
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
    LatestRatesPort,
    SeoulDistrictNamesPort,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.candidates import select_candidates
from apps.funding.domain.services.support_guide import SupportItem, build_support_guide

_DISTRICT_CODE_LENGTH = 5  # 행정동 코드 앞 5자리 = 자치구 코드


def _to_dto(entity: FundingProgram) -> FundingProgramDto:
    fields = asdict(entity)
    fields.pop("posted_at")
    fields.pop("source_updated_at")
    return FundingProgramDto(**fields)


def _to_support_dto(item: SupportItem) -> SupportItemDto:
    return SupportItemDto(
        program=_to_dto(item.candidate.program),
        why=item.why,
        district_match=item.district_match,
        industry_match=item.industry_match,
    )


class FundingProgramInteractor(FundingProgramUseCase):
    def __init__(
        self,
        repository: FundingProgramRepositoryPort,
        gateway: FundingSearchGatewayPort,
        seoul_districts: SeoulDistrictNamesPort | None = None,
        district_lookup: DistrictNameLookupPort | None = None,
        rates: LatestRatesPort | None = None,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._seoul_districts = seoul_districts
        self._district_lookup = district_lookup
        self._rates = rates

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
        """모집 중 공고 — `is_expired` 플래그와 마감일을 **둘 다** 본다.

        플래그는 일 배치(`refresh_expirations`)가 갱신하므로 설계상 최대 하루 낡는다. 어제
        마감한 공고가 다음 05:10까지 "모집 중"으로 남는 창이 있다 — 후보 필터
        (`domain/services/candidates.py`)와 같은 방어를 목록에도 둔다.
        """
        today = date.today()
        return [
            _to_dto(program)
            for program in self._repository.list_open(limit)
            if not program.is_past_deadline(today)
        ]

    def list_candidates(
        self,
        industry_id: str | None,
        external_funding_need: int | None,
        stage: str | None,
    ) -> FundingCandidateListDto:
        district_names = (
            self._seoul_districts.names() if self._seoul_districts is not None else frozenset()
        )
        selected = select_candidates(
            self._repository.list_open_all(),
            seoul_district_names=district_names,
            today=date.today(),
            stage=stage,
        )
        return FundingCandidateListDto(
            candidates=[
                FundingCandidateDto(program=_to_dto(c.program), why=c.why) for c in selected
            ],
            industry_id=industry_id,
            external_funding_need=external_funding_need,
            stage=stage,
        )

    def support_guide(self, region_code: str | None, industry_id: str | None) -> SupportGuideDto:
        district_name = (
            self._district_lookup.name_of(region_code[:_DISTRICT_CODE_LENGTH])
            if region_code and self._district_lookup is not None
            else None
        )
        guide = build_support_guide(
            self._repository.list_open_all(),
            seoul_district_names=(
                self._seoul_districts.names() if self._seoul_districts is not None else frozenset()
            ),
            district_name=district_name,
            industry_id=industry_id,
            today=date.today(),
        )
        return SupportGuideDto(
            region_code=region_code,
            district_name=district_name,
            industry_id=industry_id,
            loans=[_to_support_dto(item) for item in guide.loans],
            district=[_to_support_dto(item) for item in guide.district],
            others=[_to_support_dto(item) for item in guide.others],
            rates=self._rates.latest() if self._rates is not None else [],
        )
