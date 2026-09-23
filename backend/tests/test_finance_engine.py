"""finance 엔진 — 대구 `tests/test_finance_engine.py` 이식 + 시연 대본 사례. 두 프로젝트가 같은 수를 낸다."""

from dataclasses import replace

from apps.finance.domain.services.engine import FinanceInput, _fixed, _profit_at, simulate

BASE = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=30_000_000, equipment_cost=10_000_000,
    monthly_rent=2_000_000, monthly_payroll=6_000_000, monthly_insurance=500_000,
    cost_ratio=0.40, fee_ratio=0.03,
    equity=50_000_000, desired_loan=20_000_000, loan_rate=0.045,
    expected_monthly_revenue=20_000_000,
)


def test_capex_and_fixed():
    r = simulate(BASE)
    assert r.capex == 60_000_000
    assert r.monthly_fixed == 2_000_000 + 75_000 + 500_000 + 6_000_000


def test_bep_revenue():
    r = simulate(BASE)
    assert abs(r.bep_revenue - r.monthly_fixed / (1 - 0.43)) < 1


def test_three_scenarios_and_payback():
    r = simulate(BASE)
    assert [s.name for s in r.scenarios] == ["비관", "기준", "낙관"]
    pess, base, opt = r.scenarios
    assert pess.monthly_revenue == 12_000_000
    assert opt.monthly_revenue == 32_000_000
    assert base.operating_profit == int(20_000_000 * (1 - 0.43)) - r.monthly_fixed
    assert base.payback_months == round(r.capex / base.operating_profit, 1)


def test_funding_gap_and_runway():
    r = simulate(BASE)
    need = r.capex + r.monthly_fixed * 6
    assert r.funding_gap == max(0, need - (50_000_000 + 20_000_000))
    pess = r.scenarios[0]
    if pess.operating_profit < 0:
        cash = 50_000_000 + 20_000_000 - r.capex
        assert pess.runway_months == round(cash / -pess.operating_profit, 1)


def test_interest_stress():
    r = simulate(BASE)
    assert r.stress[0].rate_delta == 0.01 and r.stress[1].rate_delta == 0.02
    assert r.stress[0].monthly_fixed > r.monthly_fixed
    at_zero = _profit_at(BASE.expected_monthly_revenue, BASE.cost_ratio + BASE.fee_ratio, _fixed(BASE, BASE.loan_rate + 0))
    assert at_zero == r.scenarios[1].operating_profit


# --- 대구 시연 대본 사례 (만원 → 원). 설계서 §7-1 — 같은 수를 내야 서로 검산이 된다 ---

DEMO = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=20_000_000, equipment_cost=10_000_000,
    monthly_rent=2_500_000, monthly_payroll=900_000, monthly_insurance=100_000,
    cost_ratio=0.57, fee_ratio=0.03,
    equity=40_000_000, desired_loan=25_000_000, loan_rate=0.048,
    expected_monthly_revenue=8_000_000,
)


def test_시연_최초안_월세_250만():
    r = simulate(DEMO)
    assert r.capex == 50_000_000
    assert r.monthly_fixed == 3_600_000  # 250 + 이자 10 + 보험 10 + 인건비 90
    assert r.bep_revenue == 9_000_000
    assert r.total_required_funds == 71_600_000
    assert r.external_funding_need == 31_600_000
    assert r.funding_gap == 6_600_000


def test_시연_현재안_월세_100만이면_부족액_0이지만_조달_필요는_남는다():
    r = simulate(replace(DEMO, monthly_rent=1_000_000))
    assert r.bep_revenue == 5_250_000
    assert r.total_required_funds == 62_600_000
    assert r.external_funding_need == 22_600_000  # "충분합니다"가 아니다
    assert r.funding_gap == 0


def test_준비금_개월수는_화면이_설명할_수_있게_노출된다():
    assert simulate(DEMO).reserve_months == 6
