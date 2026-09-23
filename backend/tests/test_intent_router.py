"""관문 라우터 검증 — myself 배선·두 요청 형태·상태 코드·에러 바디 (Fake 포트)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.intent.adapter.inbound.api.v1.intent_router import get_intent_use_case, router
from apps.intent.app.use_cases.intent_interactor import IntentInteractor
from tests.test_intent_interactor import FakeFacts, FakeLlm, FakeMasters


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_intent_use_case] = lambda: IntentInteractor(
        FakeMasters(), FakeFacts(), FakeLlm(None)
    )
    return TestClient(app)


def test_myself는_배선만_확인한다(client):
    response = client.get("/intent/myself")

    assert response.status_code == 200
    assert response.json()["region_code"] == "myself"
    assert response.json()["diagnosis"]["sentence"]


def test_A유형_문장은_진단이_붙은_200이다(client):
    body = client.post("/intent", json={"text": "역삼1동에 카페, 예산 5천"}).json()

    assert body["intent_type"] == "A"
    assert body["region_code"] == "1168064000" and body["budget_krw"] == 50_000_000
    assert body["diagnosis"]["peak_sales_band"] == "11_14"
    assert body["source"] == "rule"


def test_B유형과_C유형도_200이다_파싱_실패는_실패가_아니다(client):
    b = client.post("/intent", json={"text": "서교동 어때"})
    c = client.post("/intent", json={"text": "예산 5천이면 뭐 할 수 있어"})

    assert b.status_code == 200 and b.json()["intent_type"] == "B"
    assert c.status_code == 200 and c.json()["intent_type"] == "C"
    assert c.json()["missing"] == ["region", "industry"]


def test_동명이동은_후보_목록으로_되묻는다(client):
    body = client.post("/intent", json={"text": "신사동 노래방"}).json()

    assert body["region_code"] is None
    assert {c["district_name"] for c in body["candidates"]} == {"강남구", "관악구"}


def test_빈_문장은_400_INTENT_TEXT_EMPTY다(client):
    for payload in ({"text": "  "}, {}):
        response = client.post("/intent", json=payload)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INTENT_TEXT_EMPTY"


def test_두_번째_형태는_코드_쌍으로_진단만_받는다(client):
    body = client.post("/intent", json={"region_code": "1168064000", "industry_id": "cafe"}).json()

    assert body["intent_type"] == "A" and body["region_name"] == "역삼1동"
    assert body["diagnosis"]["sentence"].startswith("역삼1동은")


def test_두_번째_형태의_없는_코드는_404다(client):
    r = client.post("/intent", json={"region_code": "9999999999", "industry_id": "cafe"})
    i = client.post("/intent", json={"region_code": "1168064000", "industry_id": "restaurant"})

    assert (r.status_code, r.json()["error"]["code"]) == (404, "REGION_NOT_FOUND")
    assert (i.status_code, i.json()["error"]["code"]) == (404, "INDUSTRY_NOT_FOUND")
