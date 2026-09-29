"""Driven Adapter — verdict BC 유스케이스 호출 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import VerdictFactsPort
from apps.verdict.app.dtos.region_industry_verdict_dto import RegionIndustryVerdictDto
from apps.verdict.dependencies.region_industry_verdict_dependencies import (
    get_region_industry_verdict_use_case,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import ADVISORY_SIGNAL_KEYS
from apps.verdict.domain.errors import IndustryNotFoundError

_NOT_JUDGED = "판정 대상 업종이 아니다 — 이 업종은 판정을 내리지 않는다"
_NO_VERDICT = "이 동×업종의 판정 행이 없다"


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


class VerdictFactsGateway(VerdictFactsPort):
    def verdict(self, region_code: str, industry_id: str) -> dict:
        try:
            dto = get_region_industry_verdict_use_case().find(region_code, industry_id)
        except IndustryNotFoundError:
            return _unavailable(_NOT_JUDGED)
        if dto is None:
            return _unavailable(_NO_VERDICT)
        return _verdict_payload(dto)

    def alternatives(self, region_code: str, industry_id: str) -> dict:
        try:
            dto = get_region_industry_verdict_use_case().alternatives(region_code, industry_id)
        except IndustryNotFoundError:
            return _unavailable(_NOT_JUDGED)
        if dto is None:
            return _unavailable(_NO_VERDICT)
        return {**asdict(dto), "available": True}


def _verdict_payload(dto: RegionIndustryVerdictDto) -> dict:
    """카드 전 필드 + 참고 신호 표시. 산출일은 JSON에 실리도록 문자열로 내린다."""
    return {
        **asdict(dto),
        "available": True,
        "signals": [
            {**asdict(signal), "advisory": signal.key in ADVISORY_SIGNAL_KEYS}
            for signal in dto.signals
        ],
        "computed_at": dto.computed_at.isoformat(),
    }
