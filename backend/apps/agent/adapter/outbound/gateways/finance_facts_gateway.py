"""Driven Adapter — finance BC 프리필 호출 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import FinanceFactsPort
from apps.finance.dependencies.finance_dependencies import get_finance_use_case

_KEYS = ("expected_monthly_revenue", "rent_per_m2", "loan_rate")  # 비용 비율은 직접 답에 쓰지 않는다


class FinanceFactsGateway(FinanceFactsPort):
    def prefill(self, region_code: str, industry_id: str) -> dict:
        prefill = get_finance_use_case().prefill(region_code, industry_id)
        return {"available": True, **{key: asdict(getattr(prefill, key)) for key in _KEYS}}
