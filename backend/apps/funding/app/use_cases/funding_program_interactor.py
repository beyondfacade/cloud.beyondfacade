import logging
from dataclasses import asdict
from datetime import date

from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateDto,
    FundingCandidateListDto,
    FundingProgramDto,
    SupportGuideDto,
    SupportItemDto,
    SupportSearchDto,
)
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.app.ports.output.funding_program_port import (
    DistrictNameLookupPort,
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
    LatestRatesPort,
    QuestionRankerPort,
    SeoulDistrictNamesPort,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.candidates import (
    DEFAULT_LIMIT,
    FundingCandidate,
    select_candidates,
)
from apps.funding.domain.services.relevance import (
    ORDER_DEADLINE,
    ORDER_RELEVANCE,
    order_by_relevance,
    relevant_ids,
)
from apps.funding.domain.services.support_guide import (
    SupportItem,
    build_support_guide,
    open_to_district,
)

LOGGER = logging.getLogger("beyondfacade.funding")

_DISTRICT_CODE_LENGTH = 5  # 행정동 코드 앞 5자리 = 자치구 코드
_QUESTION_MAX = 200  # 자유 입력이라 거절(422)하지 않고 자른다


def _normalize_question(question: str | None) -> str | None:
    """앞뒤 공백을 자르고 200자에서 자른다 — 비면 질문이 없는 것이다."""
    return (question or "").strip()[:_QUESTION_MAX] or None


class _UnavailableRanker(QuestionRankerPort):
    """랭커가 배선되지 않은 인터랙터 — 랭킹 실패와 똑같이 다뤄진다 (Null Object)."""

    def rank(self, question: str, program_ids: list[str]) -> list[tuple[str, float]]:
        raise RuntimeError("질문 정렬이 연결되지 않았습니다")


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
        ranker: QuestionRankerPort | None = None,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._seoul_districts = seoul_districts
        self._district_lookup = district_lookup
        self._rates = rates
        self._ranker = ranker or _UnavailableRanker()

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
        region_code: str | None = None,
        question: str | None = None,
    ) -> FundingCandidateListDto:
        district_names = (
            self._seoul_districts.names() if self._seoul_districts is not None else frozenset()
        )
        programs = self._repository.list_open_all()
        # 자르기 전 전체 — 구 전용 제외·질문 정렬 뒤에 8건을 채운다
        selected = select_candidates(
            programs,
            seoul_district_names=district_names,
            today=date.today(),
            stage=stage,
            limit=len(programs),
        )
        if region_code:
            district_name = self._district_name(region_code)
            selected = [
                c for c in selected if open_to_district(c.program, district_names, district_name)
            ]
        selected, order = self._ordered(selected, _normalize_question(question))
        return FundingCandidateListDto(
            candidates=[
                FundingCandidateDto(program=_to_dto(c.program), why=c.why)
                for c in selected[:DEFAULT_LIMIT]
            ],
            industry_id=industry_id,
            external_funding_need=external_funding_need,
            stage=stage,
            order=order,
        )

    def _ordered(
        self, candidates: list[FundingCandidate], question: str | None
    ) -> tuple[list[FundingCandidate], str]:
        """질문이 있고 기준선을 통과한 공고가 있으면 그 공고를 앞에, 아니면 규칙 순서 그대로."""
        if question is None:
            return candidates, ORDER_DEADLINE
        relevant = self._relevant(question, candidates)
        if not relevant:
            return candidates, ORDER_DEADLINE
        return order_by_relevance(candidates, relevant), ORDER_RELEVANCE

    def _relevant(self, question: str, candidates: list) -> list[str] | None:
        """기준선을 통과한 program_id(가까운 순) — 실패하면 경고 한 줄을 남기고 None (화면·리포트는 멈추지 않는다)."""
        try:
            return relevant_ids(self._ranker.rank(question, [c.program.program_id for c in candidates]))
        except Exception as error:
            LOGGER.warning("질문 정렬 실패 — 규칙 순서로 돌려준다: %s: %s", type(error).__name__, error)
            return None

    def _district_name(self, region_code: str | None) -> str | None:
        if not region_code or self._district_lookup is None:
            return None
        return self._district_lookup.name_of(region_code[:_DISTRICT_CODE_LENGTH])

    def support_guide(
        self, region_code: str | None, industry_id: str | None, question: str | None = None
    ) -> SupportGuideDto:
        district_name = self._district_name(region_code)
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
            search=self._search(guide.items, _normalize_question(question)),
        )

    def _search(self, items: list[SupportItem], question: str | None) -> SupportSearchDto | None:
        """묶음 구분 없이 기준선을 통과한 공고 전부(가까운 순). 색인 없는 공고는 관련도를 몰라 넣지 않는다.
        정렬에 실패하면 규칙 순서로 채우지 **않는다** — "검색 결과"라면서 마감 순을 내면 거짓이다."""
        if question is None:
            return None
        relevant = self._relevant(question, items)
        if relevant is None:
            return SupportSearchDto(query=question, available=False, items=[])
        by_id = {item.program.program_id: item for item in items}
        return SupportSearchDto(
            query=question,
            available=True,
            items=[_to_support_dto(by_id[program_id]) for program_id in relevant],
        )
