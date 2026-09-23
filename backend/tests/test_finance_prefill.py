"""finance 프리필 인터랙터 — 실측 원천 셋과 단서, 권역 매핑 (Fake 포트, DB 없음)."""

import pytest

from apps.finance.app.dtos.finance_dto import RateBasis, RentBasis, RevenueBasis
from apps.finance.app.ports.output.finance_port import (
    LoanRateFactsPort,
    MasterLookupPort,
    RentFactsPort,
    RevenueFactsPort,
)
from apps.finance.app.use_cases.finance_interactor import FinanceInteractor
from apps.finance.domain.errors import IndustryNotFoundError, RegionNotFoundError
from apps.finance.domain.value_objects.cost_ratios import COST_RATIO_BY_INDUSTRY
from apps.finance.domain.value_objects.rent_zones import RENT_ZONES, RENT_ZONE_BY_DISTRICT, rent_zone_of


class FakeMasters(MasterLookupPort):
    def district_of_region(self, region_code):
        return {"1168064000": "11680", "1144071000": "11440"}.get(region_code)

    def industry_exists(self, industry_id):
        return industry_id in COST_RATIO_BY_INDUSTRY


class FakeRevenue(RevenueFactsPort):
    def __init__(self, basis):
        self.basis = basis

    def latest_quarterly_sales_per_store(self, region_code, industry_id):
        return self.basis


class FakeRent(RentFactsPort):
    def __init__(self):
        self.asked: list[str] = []

    def latest_zone_rent(self, zone_path):
        self.asked.append(zone_path)
        return RentBasis(region_path=zone_path, period="2026Q2", medium_large_per_m2=65.51, small_per_m2=64.56)


class FakeRates(LoanRateFactsPort):
    def latest_facility_rate(self):
        return RateBasis(rate_type="loan_facility", period="202607", rate_pct=4.05)


_REVENUE = RevenueBasis(
    year_quarter="20254", quarterly_sales=35_327_445_013, store_count=400,
    source_codes=["CS100006", "CS100008", "CS100010"],
)


def _interactor(revenue=_REVENUE, rent=None):
    return FinanceInteractor(FakeMasters(), FakeRevenue(revenue), rent or FakeRent(), FakeRates())


def test_월매출은_분기_매출_합을_점포_합으로_나누고_3으로_나눈다():
    dto = _interactor().prefill("1168064000", "cafe")
    assert dto.expected_monthly_revenue.value == round(35_327_445_013 / 400 / 3)
    assert dto.expected_monthly_revenue.basis["source_codes"] == ["CS100006", "CS100008", "CS100010"]
    assert "400곳" in dto.expected_monthly_revenue.caveat


def test_매출_없는_조합은_404가_아니라_값_null이다():
    dto = _interactor(revenue=None).prefill("1168064000", "childcare")
    assert dto.expected_monthly_revenue.value is None
    assert "직접" in dto.expected_monthly_revenue.caveat


def test_임대료는_구를_권역으로_바꿔_묻는다():
    rent = FakeRent()
    dto = _interactor(rent=rent).prefill("1168064000", "cafe")
    assert rent.asked == ["서울>강남"]
    assert dto.rent_per_m2.value == 65.51
    assert dto.rent_per_m2.basis["level"] == "권역" and dto.rent_per_m2.basis["small_per_m2"] == 64.56
    assert "강남 권역" in dto.rent_per_m2.caveat


def test_구_25개가_전부_권역_넷_중_하나에_매핑된다():
    assert len(RENT_ZONE_BY_DISTRICT) == 25
    assert set(RENT_ZONE_BY_DISTRICT.values()) == set(RENT_ZONES)
    assert rent_zone_of("11680") == "서울>강남" and rent_zone_of("11140") == "서울>도심"
    assert rent_zone_of("11440") == "서울>영등포신촌" and rent_zone_of("11710") == "서울>기타"
    assert rent_zone_of("27110") is None  # 서울 밖


def test_금리는_ECOS_시설자금_최신을_비율로_준다():
    dto = _interactor().prefill("1168064000", "cafe")
    assert dto.loan_rate.value == pytest.approx(0.0405)
    assert dto.loan_rate.basis == {"rate_type": "loan_facility", "period": "202607", "rate_pct": 4.05, "source": "ECOS"}


def test_원가율은_업종_벤치마크이고_자기자본은_서버가_채우지_않는다():
    dto = _interactor().prefill("1168064000", "cafe")
    assert dto.cost_ratio.value == 0.35 and dto.cost_ratio.basis["kind"] == "industry_benchmark"
    assert dto.equity is None


def test_없는_동은_RegionNotFoundError_없는_업종은_IndustryNotFoundError():
    with pytest.raises(RegionNotFoundError):
        _interactor().prefill("9999999999", "cafe")
    with pytest.raises(IndustryNotFoundError):
        _interactor().prefill("1168064000", "restaurant")


def test_myself는_시연_사례를_엔진에_실제로_통과시킨다():
    r = _interactor().myself()
    assert (r.bep_revenue, r.external_funding_need, r.funding_gap) == (9_000_000, 31_600_000, 6_600_000)
