"""finance 라우터 — 배선(myself)·simulate 입력 검증(422)·prefill 계약(200/404) (Fake 포트)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.finance.adapter.inbound.api.v1.finance_router import get_finance_use_case, router
from apps.finance.app.use_cases.finance_interactor import FinanceInteractor
from tests.test_finance_prefill import _REVENUE, FakeMasters, FakeRates, FakeRent, FakeRevenue

_VALID = {
    "deposit": 20_000_000, "key_money": 0, "interior_cost": 30_000_000, "equipment_cost": 10_000_000,
    "monthly_rent": 2_000_000, "monthly_payroll": 6_000_000, "monthly_insurance": 500_000,
    "cost_ratio": 0.40, "fee_ratio": 0.03,
    "equity": 50_000_000, "desired_loan": 20_000_000, "loan_rate": 0.045,
    "expected_monthly_revenue": 20_000_000,
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_finance_use_case] = lambda: FinanceInteractor(
        FakeMasters(), FakeRevenue(_REVENUE), FakeRent(), FakeRates()
    )
    return TestClient(app)


def test_myself는_엔진을_통과한_결과를_준다(client):
    body = client.get("/finance/myself").json()
    assert body["external_funding_need"] == 31_600_000 and body["reserve_months"] == 6


def test_simulate_정상_입력은_200이고_네_갈래가_같이_온다(client):
    response = client.post("/finance/simulate", json={**_VALID, "monthly_rent": 1_000_000, "cost_ratio": 0.57,
                                                      "interior_cost": 20_000_000, "monthly_payroll": 900_000,
                                                      "monthly_insurance": 100_000, "equity": 40_000_000,
                                                      "desired_loan": 25_000_000, "loan_rate": 0.048,
                                                      "expected_monthly_revenue": 8_000_000})
    assert response.status_code == 200
    body = response.json()
    assert body["total_required_funds"] == 62_600_000
    assert body["external_funding_need"] == 22_600_000
    assert body["funding_gap"] == 0
    assert [s["name"] for s in body["scenarios"]] == ["비관", "기준", "낙관"]
    assert len(body["stress"]) == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"cost_ratio": 0.97, "fee_ratio": 0.03},  # 변동비율 = 1 → BEP 0 나눗셈
        {"cost_ratio": 0.9, "fee_ratio": 0.2},  # 변동비율 > 1 → 음수 BEP
        {"fee_ratio": -0.01},
        {"loan_rate": -0.01},
        {"deposit": -1},
        {"expected_monthly_revenue": -1},
    ],
)
def test_simulate_잘못된_입력은_500이_아니라_422다(client, overrides):
    assert client.post("/finance/simulate", json={**_VALID, **overrides}).status_code == 422


def test_prefill은_값마다_출처와_단서를_준다(client):
    response = client.get("/finance/prefill", params={"region": "1168064000", "industry": "cafe"})
    assert response.status_code == 200
    body = response.json()
    for key in ("expected_monthly_revenue", "rent_per_m2", "cost_ratio", "loan_rate"):
        assert {"value", "basis", "caveat"} <= set(body[key]), key
    assert body["expected_monthly_revenue"]["value"] == round(35_327_445_013 / 400 / 3)
    assert body["rent_per_m2"]["unit"] == "천원/㎡/월"
    assert body["equity"] is None


def test_prefill_없는_동은_404_REGION_NOT_FOUND(client):
    response = client.get("/finance/prefill", params={"region": "9999999999", "industry": "cafe"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "REGION_NOT_FOUND"


def test_prefill_없는_업종은_404_INDUSTRY_NOT_FOUND(client):
    response = client.get("/finance/prefill", params={"region": "1168064000", "industry": "restaurant"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "INDUSTRY_NOT_FOUND"


def test_prefill_파라미터_누락은_422(client):
    assert client.get("/finance/prefill", params={"region": "1168064000"}).status_code == 422


# --- POST /finance/questions (설계서 §4) ---

_QUESTIONS_INPUT = {
    "deposit": 20_000_000, "key_money": 0, "interior_cost": 20_000_000,
    "equipment_cost": 10_000_000, "monthly_rent": 2_500_000, "monthly_payroll": 900_000,
    "monthly_insurance": 100_000, "cost_ratio": 0.57, "fee_ratio": 0.03,
    "equity": 40_000_000, "desired_loan": 25_000_000, "loan_rate": 0.048,
    "expected_monthly_revenue": 8_000_000,
}


def test_questions_시연_사례에서_gap_질문_둘을_돌려준다(client):
    response = client.post("/finance/questions", json={"input": _QUESTIONS_INPUT})

    assert response.status_code == 200
    questions = response.json()["questions"]
    gaps = [q for q in questions if q["kind"] == "gap"]
    assert len(gaps) == 2
    assert "3,160만 원" in gaps[0]["text"]
    assert all(q["basis"] for q in questions)


def test_questions_입력_말고는_전부_선택이다(client):
    """화면이 단계·후보를 아직 모아두지 않았어도 초안이 나온다."""
    response = client.post("/finance/questions", json={"input": _QUESTIONS_INPUT})

    assert response.status_code == 200
    assert response.json()["questions"]


def test_questions_후보_제목을_실어_보내면_절차_질문이_붙는다(client):
    body = {"input": _QUESTIONS_INPUT, "candidate_titles": ["소상공인 정책자금", "창업 지원"]}

    questions = client.post("/finance/questions", json=body).json()["questions"]

    assert sum(1 for q in questions if "해당하는지" in q["text"]) == 2


def test_questions_계산_결과는_받지_않는다(client):
    """서버가 input으로 다시 계산한다 — 클라이언트 결과를 신뢰하지 않는다(T3 원칙)."""
    body = {"input": _QUESTIONS_INPUT, "result": {"external_funding_need": 999}}

    questions = client.post("/finance/questions", json=body).json()["questions"]

    assert "3,160만 원" in questions[0]["text"]  # 보낸 999가 아니라 서버 계산값


def test_questions_변동비율이_1_이상이면_422다(client):
    body = {"input": {**_QUESTIONS_INPUT, "cost_ratio": 0.7, "fee_ratio": 0.4}}

    assert client.post("/finance/questions", json=body).status_code == 422
