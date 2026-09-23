"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.finance.adapter.outbound.gateways.loan_rate_facts_gateway import LoanRateFactsGateway
from apps.finance.adapter.outbound.gateways.master_lookup_gateway import MasterLookupGateway
from apps.finance.adapter.outbound.gateways.rent_facts_gateway import RentFactsGateway
from apps.finance.adapter.outbound.gateways.revenue_facts_gateway import RevenueFactsGateway
from apps.finance.app.ports.input.finance_use_case import FinanceUseCase
from apps.finance.app.use_cases.finance_interactor import FinanceInteractor


def get_finance_use_case() -> FinanceUseCase:
    return FinanceInteractor(
        masters=MasterLookupGateway(),
        revenue=RevenueFactsGateway(),
        rent=RentFactsGateway(),
        rates=LoanRateFactsGateway(),
    )
