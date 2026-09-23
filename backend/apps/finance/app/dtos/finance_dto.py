"""finance BC DTO — 엔진 입출력과 프리필 (Router ↔ Interactor 경계의 애플리케이션 언어)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinanceInputDto:
    """엔진 입력 13필드 — 대구 `FinanceInput`과 같은 이름·단위(원, 비율)."""

    deposit: int
    key_money: int
    interior_cost: int
    equipment_cost: int
    monthly_rent: int
    monthly_payroll: int
    monthly_insurance: int
    cost_ratio: float
    fee_ratio: float
    equity: int
    desired_loan: int
    loan_rate: float
    expected_monthly_revenue: int


@dataclass(frozen=True)
class ScenarioDto:
    name: str
    monthly_revenue: int
    variable_cost: int
    operating_profit: int
    payback_months: float | None
    runway_months: float | None


@dataclass(frozen=True)
class StressDto:
    rate_delta: float
    monthly_fixed: int
    base_operating_profit: int


@dataclass(frozen=True)
class FinanceResultDto:
    capex: int
    monthly_fixed: int
    bep_revenue: int
    funding_gap: int  # 희망대출 반영 후 부족액 — 보조
    reserve_months: int
    operating_reserve: int
    total_required_funds: int
    external_funding_need: int  # 자기자본 외 조달 필요 — 헤드라인
    scenarios: list[ScenarioDto] = field(default_factory=list)
    stress: list[StressDto] = field(default_factory=list)


# --- 프리필 원천 사실 (Driven Port가 돌려주는 단위) ---


@dataclass(frozen=True)
class RevenueBasis:
    """행정동×업종의 최신 분기 매출·점포 합 — CS 코드 여러 개면 게이트웨이가 합산한 값."""

    year_quarter: str
    quarterly_sales: int  # 분기 합 (원)
    store_count: int
    source_codes: list[str]


@dataclass(frozen=True)
class RentBasis:
    region_path: str  # "서울>강남"
    period: str  # "2026Q2"
    medium_large_per_m2: float | None  # 천원/㎡/월
    small_per_m2: float | None


@dataclass(frozen=True)
class RateBasis:
    rate_type: str
    period: str  # YYYYMM
    rate_pct: float  # 연% (4.05)


# --- 프리필 응답 ---


@dataclass(frozen=True)
class PrefillValueDto:
    """값 하나 + 출처 + 단서. 화면은 값을 채우되 어디서 온 값인지 항상 보인다 (후보.md 항목 1)."""

    value: float | int | None
    basis: dict
    caveat: str
    unit: str | None = None


@dataclass(frozen=True)
class PrefillDto:
    region_code: str
    industry_id: str
    expected_monthly_revenue: PrefillValueDto
    rent_per_m2: PrefillValueDto
    cost_ratio: PrefillValueDto
    loan_rate: PrefillValueDto
    equity: None = None  # 관문의 budget이 URL로 온다 — 서버는 채우지 않는다
