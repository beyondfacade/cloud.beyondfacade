"""finance 라우터 스키마 — 대구 `finance_schema.py`의 검증 규칙을 그대로 옮겼다."""

from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

_Won = Annotated[int, Field(ge=0)]  # 금액(원) — 음수 불가
_Ratio = Annotated[float, Field(ge=0, lt=1)]  # 비율 0 이상 1 미만


class SimulateRequest(BaseModel):
    deposit: _Won
    key_money: _Won
    interior_cost: _Won
    equipment_cost: _Won
    monthly_rent: _Won
    monthly_payroll: _Won
    monthly_insurance: _Won
    cost_ratio: _Ratio
    fee_ratio: _Ratio
    equity: _Won
    desired_loan: _Won
    loan_rate: _Ratio
    expected_monthly_revenue: _Won

    @model_validator(mode="after")
    def _variable_ratio_below_one(self) -> Self:
        """BEP 매출 = 고정비/(1-변동비율) — 변동비율 ≥ 1 이면 0 나눗셈·음수 BEP (422)."""
        if self.cost_ratio + self.fee_ratio >= 1:
            raise ValueError("cost_ratio + fee_ratio 는 1 미만이어야 합니다")
        return self


class ScenarioResponse(BaseModel):
    name: str
    monthly_revenue: int
    variable_cost: int
    operating_profit: int
    payback_months: float | None
    runway_months: float | None


class StressResponse(BaseModel):
    rate_delta: float
    monthly_fixed: int
    base_operating_profit: int


class SimulateResponse(BaseModel):
    capex: int
    monthly_fixed: int
    bep_revenue: int
    funding_gap: int  # 희망대출 반영 후 남는 부족액 — 보조
    reserve_months: int
    operating_reserve: int
    total_required_funds: int
    external_funding_need: int  # 자기자본 외 조달 필요 — 헤드라인
    scenarios: list[ScenarioResponse]
    stress: list[StressResponse]


class PrefillValueResponse(BaseModel):
    """값 + 출처 + 단서. 화면은 출처 배지를 값 옆에 띄운다."""

    value: float | None
    basis: dict
    caveat: str
    unit: str | None = None


class PrefillResponse(BaseModel):
    region_code: str
    industry_id: str
    expected_monthly_revenue: PrefillValueResponse
    rent_per_m2: PrefillValueResponse
    cost_ratio: PrefillValueResponse
    loan_rate: PrefillValueResponse
    equity: None = None  # 관문의 budget이 URL로 온다


class QuestionProfileRequest(BaseModel):
    """창업 단계 — null·"unknown"은 모름이다. 0·아니오로 바꾸지 않는다."""

    business_registered: bool | None = None
    guarantee_status: str = "unknown"
    policy_confirmation_status: str = "unknown"


class QuestionsRequest(BaseModel):
    """계획 초안 요약. **계산 결과는 받지 않는다** — 서버가 `input`으로 다시 계산한다."""

    input: SimulateRequest
    unconfirmed: list[str] = Field(default_factory=list)
    prefilled: list[str] = Field(default_factory=list)
    candidate_titles: list[str] = Field(default_factory=list)
    profile: QuestionProfileRequest = Field(default_factory=QuestionProfileRequest)
    change_reason: str = ""


class QuestionResponse(BaseModel):
    text: str
    basis: str  # 어느 수치에서 나왔는지
    kind: str  # gap | assumption | procedure


class QuestionsResponse(BaseModel):
    """서버가 주는 것은 초안이다 — 사용자가 편집·삭제·추가한다."""

    questions: list[QuestionResponse]
