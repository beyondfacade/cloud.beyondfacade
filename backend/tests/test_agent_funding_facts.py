"""funding_facts_gateway — 공고 후보를 프론트 카드가 읽을 키로 옮기는 경계 (DB 없음, 유스케이스 대역)."""

from datetime import date

from apps.agent.adapter.outbound.gateways import funding_facts_gateway
from apps.agent.adapter.outbound.gateways.funding_facts_gateway import FundingFactsGateway
from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateDto,
    FundingCandidateListDto,
    FundingProgramDto,
)

_PROGRAM = FundingProgramDto(
    program_id="PBLN_000000000126191",
    source="bizinfo",
    title="2026년 소상공인 정책자금",
    org="중소벤처기업부",
    url="https://www.bizinfo.go.kr/x",
    apply_period="2026-09-03 ~ 2026-09-17",
    field_category="금융",
    target_text="중소기업",
    deadline=date(2026, 9, 17),
    summary="운전자금 융자",
)


class _FakeFundingUseCase:
    def list_candidates(self, industry_id, external_funding_need, stage):
        return FundingCandidateListDto(
            candidates=[FundingCandidateDto(program=_PROGRAM, why="서울 소재 미만료 공고")],
            industry_id=industry_id,
            external_funding_need=external_funding_need,
            stage=stage,
        )


def test_공고_후보는_카드가_읽는_키를_싣는다(monkeypatch):
    """프론트 `ReportFundingCandidate`가 읽는 키다 — `program_id`가 없으면 카드 key가 흔들린다."""
    monkeypatch.setattr(
        funding_facts_gateway, "get_funding_program_use_case", _FakeFundingUseCase
    )

    result = FundingFactsGateway().candidates("korean_food", None, None)

    candidate = result["candidates"][0]
    assert {"program_id", "title", "org", "why", "summary", "url"} <= set(candidate)
    assert candidate["program_id"] == "PBLN_000000000126191"
    assert candidate["field_category"] == "금융"  # 수집기가 `target`으로 옮긴다
    assert candidate["why"] == "서울 소재 미만료 공고"
