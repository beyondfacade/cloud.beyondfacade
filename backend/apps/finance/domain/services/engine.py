"""재무 시뮬레이션 결정론 엔진 — `cloud.localhostdaegu` `apps/finance/domain/engine.py`(2026-09-18, 자작)를
산식 한 글자 바꾸지 않고 옮겼다. 두 프로젝트가 같은 수를 내야 서로 검산이 된다.

CAPEX=보증금+권리금+인테리어+설비 / OPEX고정=월세+이자+보험+인건비 /
변동비=매출×(원가율+수수료율) / BEP매출=고정비/(1-변동비율) /
시나리오 비관·기준·낙관 = 기준 × 0.6 / 1.0 / 1.6

헤드라인은 `funding_gap`(희망대출 반영 후 부족액)이 아니라 `external_funding_need`(자기자본 외 조달
필요)다 — 희망대출은 아직 빌리지 않은 돈이라 부족액 0원이 "충분하다"를 뜻하지 않는다(설계서 §1).
"""
from dataclasses import dataclass, field

_SCENARIO_MULTIPLIERS = (("비관", 0.6), ("기준", 1.0), ("낙관", 1.6))
_WORKING_CAPITAL_MONTHS = 6
_STRESS_DELTAS = (0.01, 0.02)

@dataclass(frozen=True)
class FinanceInput:
    deposit: int; key_money: int; interior_cost: int; equipment_cost: int
    monthly_rent: int; monthly_payroll: int; monthly_insurance: int
    cost_ratio: float; fee_ratio: float
    equity: int; desired_loan: int; loan_rate: float
    expected_monthly_revenue: int

@dataclass(frozen=True)
class SimulationScenario:
    name: str; monthly_revenue: int; variable_cost: int
    operating_profit: int; payback_months: float | None; runway_months: float | None

@dataclass(frozen=True)
class StressResult:
    rate_delta: float; monthly_fixed: int; base_operating_profit: int

@dataclass(frozen=True)
class FinanceResult:
    capex: int; monthly_fixed: int; bep_revenue: int; funding_gap: int
    # funding_gap = 희망대출 반영 후 남는 부족액. external_funding_need 와 다르다 — 전환계획 §4-1
    reserve_months: int; operating_reserve: int
    total_required_funds: int; external_funding_need: int
    scenarios: list[SimulationScenario] = field(default_factory=list)
    stress: list[StressResult] = field(default_factory=list)

def _monthly_interest(principal: int, rate: float) -> int:
    return int(principal * rate / 12)

def _fixed(inp: FinanceInput, rate: float) -> int:
    return inp.monthly_rent + _monthly_interest(inp.desired_loan, rate) + inp.monthly_insurance + inp.monthly_payroll

def _profit_at(revenue: int, var_ratio: float, fixed: int) -> int:
    """Canonical profit formula: revenue - variable_costs - fixed_costs.
    Unifies scenarios and stress calculation paths."""
    return revenue - int(revenue * var_ratio) - fixed

def simulate(inp: FinanceInput) -> FinanceResult:
    capex = inp.deposit + inp.key_money + inp.interior_cost + inp.equipment_cost
    fixed = _fixed(inp, inp.loan_rate)
    var_ratio = inp.cost_ratio + inp.fee_ratio
    bep_revenue = int(fixed / (1 - var_ratio))
    available_cash = inp.equity + inp.desired_loan - capex
    operating_reserve = fixed * _WORKING_CAPITAL_MONTHS
    total_required_funds = capex + operating_reserve
    external_funding_need = max(0, total_required_funds - inp.equity)
    funding_gap = max(0, total_required_funds - inp.equity - inp.desired_loan)

    scenarios = []
    for name, mult in _SCENARIO_MULTIPLIERS:
        revenue = int(inp.expected_monthly_revenue * mult)
        variable = int(revenue * var_ratio)
        profit = _profit_at(revenue, var_ratio, fixed)
        payback = round(capex / profit, 1) if profit > 0 else None      # 영업이익 ≤ 0 → 회수 불가
        runway = round(available_cash / -profit, 1) if (profit < 0 and available_cash > 0) else None
        scenarios.append(SimulationScenario(name, revenue, variable, profit, payback, runway))

    stress = [StressResult(d, _fixed(inp, inp.loan_rate + d), _profit_at(inp.expected_monthly_revenue, var_ratio, _fixed(inp, inp.loan_rate + d)))
              for d in _STRESS_DELTAS]
    return FinanceResult(capex, fixed, bep_revenue, funding_gap,
                         _WORKING_CAPITAL_MONTHS, operating_reserve,
                         total_required_funds, external_funding_need,
                         scenarios, stress)
