"""업종별 원가율(변동비 중 매출원가 비율) 근사 벤치마크 (설계서 §4-3).

전부 "근사"다 — 사용자가 원가 구조를 알면 폼에서 고친다. 겹치는 6종은 대구 분화본
`features/simulator/lib/form-defaults.ts`(소상공인 실태조사 근사)의 값을 그대로 썼고, 우리에게만
있는 4종은 아래 근거로 정했다.

- academy 0.20 — 학원은 강사 인건비가 고정비(월 인건비)로 잡히고 교재·교구 변동비는 낮다
- childcare 0.30 — 급식·교재·소모품. 보육료 매출 대비 재료비 성격
- convenience_store 0.72 — 편의점은 상품 매입원가가 매출의 7할 안팎(본사 공급가). 소상공인 실태조사
  도소매 원가율 근사
- real_estate 0.05 — 중개보수 매출에 원가가 거의 없다. 광고·플랫폼 수수료 정도
"""

COST_RATIO_BY_INDUSTRY: dict[str, float] = {
    "cafe": 0.35,
    "hair_salon": 0.25,
    "gym": 0.15,
    "billiard": 0.20,
    "karaoke": 0.20,
    "pc_bang": 0.20,
    "academy": 0.20,
    "childcare": 0.30,
    "convenience_store": 0.72,
    "real_estate": 0.05,
}

DEFAULT_COST_RATIO = 0.40  # 미등록 업종 폴백 (대구와 같음)


def cost_ratio_of(industry_id: str) -> float:
    return COST_RATIO_BY_INDUSTRY.get(industry_id, DEFAULT_COST_RATIO)
