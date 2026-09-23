"""Driven Adapter — finance BC 엔진 호출 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import FinanceFactsPort
from apps.finance.app.dtos.finance_dto import FinanceInputDto
from apps.finance.dependencies.finance_dependencies import get_finance_use_case

_ASSUMPTIONS = "공시 평균 금리 기반 예상치 — 실제 심사 금리·한도와 다를 수 있음"


class FinanceFactsGateway(FinanceFactsPort):
    def simulate(self, input: dict) -> dict:
        result = get_finance_use_case().simulate(FinanceInputDto(**input))
        return {**asdict(result), "assumptions": _ASSUMPTIONS}
