from dataclasses import asdict

from apps.finance.app.dtos.finance_dto import (
    FinanceInputDto,
    FinanceResultDto,
    PrefillDto,
    PrefillValueDto,
    ScenarioDto,
    StressDto,
)
from apps.finance.app.ports.input.finance_use_case import FinanceUseCase
from apps.finance.app.ports.output.finance_port import (
    LoanRateFactsPort,
    MasterLookupPort,
    RentFactsPort,
    RevenueFactsPort,
)
from apps.finance.domain.errors import IndustryNotFoundError, RegionNotFoundError
from apps.finance.domain.services.engine import FinanceInput, FinanceResult, simulate
from apps.finance.domain.value_objects.cost_ratios import cost_ratio_of
from apps.finance.domain.value_objects.rent_zones import rent_zone_of

_MONTHS_PER_QUARTER = 3

# §12 배선 검증용 — 대구 시연 대본 사례(만원 → 원)
_MYSELF_INPUT = FinanceInputDto(
    deposit=20_000_000, key_money=0, interior_cost=20_000_000, equipment_cost=10_000_000,
    monthly_rent=2_500_000, monthly_payroll=900_000, monthly_insurance=100_000,
    cost_ratio=0.57, fee_ratio=0.03,
    equity=40_000_000, desired_loan=25_000_000, loan_rate=0.048,
    expected_monthly_revenue=8_000_000,
)


def _to_result_dto(result: FinanceResult) -> FinanceResultDto:
    return FinanceResultDto(
        capex=result.capex,
        monthly_fixed=result.monthly_fixed,
        bep_revenue=result.bep_revenue,
        funding_gap=result.funding_gap,
        reserve_months=result.reserve_months,
        operating_reserve=result.operating_reserve,
        total_required_funds=result.total_required_funds,
        external_funding_need=result.external_funding_need,
        scenarios=[ScenarioDto(**asdict(s)) for s in result.scenarios],
        stress=[StressDto(**asdict(s)) for s in result.stress],
    )


class FinanceInteractor(FinanceUseCase):
    def __init__(
        self,
        masters: MasterLookupPort,
        revenue: RevenueFactsPort,
        rent: RentFactsPort,
        rates: LoanRateFactsPort,
    ) -> None:
        self._masters = masters
        self._revenue = revenue
        self._rent = rent
        self._rates = rates

    def myself(self) -> FinanceResultDto:
        return self.simulate(_MYSELF_INPUT)

    def simulate(self, request: FinanceInputDto) -> FinanceResultDto:
        return _to_result_dto(simulate(FinanceInput(**asdict(request))))

    def prefill(self, region_code: str, industry_id: str) -> PrefillDto:
        district_code = self._masters.district_of_region(region_code)
        if district_code is None:
            raise RegionNotFoundError(region_code)
        if not self._masters.industry_exists(industry_id):
            raise IndustryNotFoundError(industry_id)
        return PrefillDto(
            region_code=region_code,
            industry_id=industry_id,
            expected_monthly_revenue=self._revenue_prefill(region_code, industry_id),
            rent_per_m2=self._rent_prefill(district_code),
            cost_ratio=PrefillValueDto(
                value=cost_ratio_of(industry_id),
                basis={"kind": "industry_benchmark", "industry_id": industry_id},
                caveat="업종 평균 근사값입니다. 원가 구조를 알면 고치세요.",
            ),
            loan_rate=self._rate_prefill(),
        )

    def _revenue_prefill(self, region_code: str, industry_id: str) -> PrefillValueDto:
        basis = self._revenue.latest_quarterly_sales_per_store(region_code, industry_id)
        if basis is None or basis.store_count <= 0:
            return PrefillValueDto(
                value=None,
                basis={},
                caveat="이 동네엔 이 업종의 매출 자료가 없습니다. 예상 월매출을 직접 넣으세요.",
                unit="원/월",
            )
        # 분기 합 ÷ 점포 수 ÷ 3 — 원천 `당월_매출_금액`은 이름과 달리 분기 합이다(게이트웨이 주석)
        monthly = round(basis.quarterly_sales / basis.store_count / _MONTHS_PER_QUARTER)
        return PrefillValueDto(
            value=monthly,
            basis={
                "year_quarter": basis.year_quarter,
                "quarterly_sales": basis.quarterly_sales,
                "store_count": basis.store_count,
                "source_codes": list(basis.source_codes),
            },
            caveat=(
                f"이 동 같은 업종 {basis.store_count:,}곳의 분기 매출을 점포 수로 나눈 평균입니다. "
                "편차가 크고 신규 점포는 평균 아래서 시작하는 경우가 많습니다."
            ),
            unit="원/월",
        )

    def _rent_prefill(self, district_code: str) -> PrefillValueDto:
        zone = rent_zone_of(district_code)
        basis = self._rent.latest_zone_rent(zone) if zone else None
        if basis is None or basis.medium_large_per_m2 is None:
            return PrefillValueDto(
                value=None,
                basis={},
                caveat="이 지역의 임대료 참고 자료가 없습니다. 월세를 직접 넣으세요.",
                unit="천원/㎡/월",
            )
        zone_name = basis.region_path.split(">")[-1]
        return PrefillValueDto(
            value=round(basis.medium_large_per_m2, 2),
            basis={
                "region_path": basis.region_path,
                "building_type": "medium_large",
                "period": basis.period,
                "level": "권역",
                "small_per_m2": None if basis.small_per_m2 is None else round(basis.small_per_m2, 2),
                "source": "R-ONE",
            },
            caveat=(
                f"행정동 단위 임대료 자료가 없어 {zone_name} 권역(R-ONE, 중대형 상가) 평균입니다. "
                "실제 매물과 다를 수 있습니다."
            ),
            unit="천원/㎡/월",
        )

    def _rate_prefill(self) -> PrefillValueDto:
        basis = self._rates.latest_facility_rate()
        if basis is None:
            return PrefillValueDto(
                value=None, basis={}, caveat="공시 금리 자료가 없습니다. 연금리를 직접 넣으세요.", unit="비율"
            )
        return PrefillValueDto(
            value=round(basis.rate_pct / 100, 4),
            basis={"rate_type": basis.rate_type, "period": basis.period, "rate_pct": basis.rate_pct, "source": "ECOS"},
            caveat="공시 평균 금리입니다. 실제 심사 금리와 다릅니다.",
            unit="비율",
        )
