"""Driven Adapter — funding BC 후보 필터 호출 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import FundingFactsPort
from apps.funding.dependencies.funding_program_dependencies import (
    get_funding_program_use_case,
)

# 자격 판정이 아니라 후보 제시임을 LLM이 매번 보게 결과에 함께 싣는다 (설계서 §6)
_DISCLAIMER = "자격 확정이 아니라 해당 가능성이 있는 공고다. 신청 자격·한도는 원문에서 확인해야 한다"


class FundingFactsGateway(FundingFactsPort):
    def candidates(
        self, industry_id: str | None, external_funding_need: int | None, stage: str | None
    ) -> dict:
        result = get_funding_program_use_case().list_candidates(
            industry_id, external_funding_need, stage
        )
        return {
            "candidates": [
                {
                    "title": c.program.title,
                    "org": c.program.org,
                    "url": c.program.url,
                    "apply_period": c.program.apply_period,
                    "deadline": c.program.deadline.isoformat() if c.program.deadline else None,
                    "field_category": c.program.field_category,
                    "summary": c.program.summary,
                    "why": c.why,
                }
                for c in result.candidates
            ],
            "industry_id": result.industry_id,
            "external_funding_need": result.external_funding_need,
            "stage": result.stage,
            "disclaimer": _DISCLAIMER,
        }
