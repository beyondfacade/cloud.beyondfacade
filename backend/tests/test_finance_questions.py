"""확인할 질문 생성 검증 — 11규칙 각각 해당/비해당, 시연 사례 (설계서 §4, DB 없음)."""

from apps.finance.domain.services.engine import FinanceInput, simulate
from apps.finance.domain.services.questions import (
    KIND_ASSUMPTION,
    KIND_GAP,
    KIND_PROCEDURE,
    QuestionContext,
    build_questions,
    to_manwon,
    topic_particle,
)

# 대구 시연 대본 사례(만원 → 원) — 월세 250만: 조달 필요 3,160만 · 부족액 660만
_DEMO = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=20_000_000, equipment_cost=10_000_000,
    monthly_rent=2_500_000, monthly_payroll=900_000, monthly_insurance=100_000,
    cost_ratio=0.57, fee_ratio=0.03,
    equity=40_000_000, desired_loan=25_000_000, loan_rate=0.048,
    expected_monthly_revenue=8_000_000,
)


def _context(finance: FinanceInput = _DEMO, **overrides) -> QuestionContext:
    base = dict(
        finance=finance,
        result=simulate(finance),
        business_registered=True,
        guarantee_status="issued",
        policy_confirmation_status="issued",
    )
    return QuestionContext(**{**base, **overrides})


def _texts(ctx: QuestionContext) -> str:
    return " ".join(q.text for q in build_questions(ctx))


def _kinds(ctx: QuestionContext) -> list[str]:
    return [q.kind for q in build_questions(ctx)]


# --- 단위·조사 ---


def test_금액은_화면과_같은_만원_단위로_쓴다():
    assert to_manwon(31_600_000) == "3,160"
    assert to_manwon(0) == "0"


def test_조사는_받침에_따라_은_는을_고른다():
    assert topic_particle("권리금") == "은"
    assert topic_particle("월세") == "는"


# --- gap 2종 ---


def test_조달_필요가_남으면_헤드라인_질문이_나온다():
    ctx = _context()

    assert "자기자본 외 3,160만 원" in _texts(ctx)
    assert KIND_GAP in _kinds(ctx)


def test_조달_필요가_0이면_그_질문이_없다():
    넉넉 = FinanceInput(**{**_DEMO.__dict__, "equity": 200_000_000})

    assert "자기자본 외" not in _texts(_context(넉넉))


def test_희망대출을_다_받아도_남으면_부족액_질문이_나온다():
    assert "660만 원이 남습니다" in _texts(_context())


def test_부족액이_0이면_그_질문이_없다():
    # 월세 100만 사례 — 부족액 0이지만 조달 필요 2,260만은 남는다
    싼월세 = FinanceInput(**{**_DEMO.__dict__, "monthly_rent": 1_000_000})
    텍스트 = _texts(_context(싼월세))

    assert "남습니다" not in 텍스트
    assert "자기자본 외 2,260만 원" in 텍스트


def test_시연_사례에서_gap_질문이_정확히_둘이다():
    assert _kinds(_context()).count(KIND_GAP) == 2


# --- assumption 5종 ---


def test_희망대출이_있으면_조건을_묻고_적용_금리를_밝힌다():
    assert "공시 평균 4.8%로 했습니다" in _texts(_context())


def test_희망대출이_0이면_그_질문이_없다():
    무대출 = FinanceInput(**{**_DEMO.__dict__, "desired_loan": 0})

    assert "예상 금리·기간·상환 방식" not in _texts(_context(무대출))


# 시연 사례는 비관 런웨이 8.9개월이라 이 규칙이 발화하지 않는다 — 자기자본을 낮춰 가용현금을 줄인다
_SHORT_RUNWAY = FinanceInput(**{**_DEMO.__dict__, "equity": 32_000_000})


def test_비관_런웨이가_6개월_미만이면_묻는다():
    ctx = _context(_SHORT_RUNWAY)
    비관 = next(s for s in ctx.result.scenarios if s.name == "비관")

    assert 비관.runway_months is not None and 비관.runway_months < 6
    assert "매출이 기준의 60%일 때" in _texts(ctx)


def test_비관_런웨이가_6개월_이상이면_묻지_않는다():
    비관 = next(s for s in _context().result.scenarios if s.name == "비관")

    assert 비관.runway_months >= 6  # 시연 사례 8.9개월
    assert "기준의 60%" not in _texts(_context())


def test_비관에서도_이익이_나면_런웨이_질문이_없다():
    여유 = FinanceInput(**{**_DEMO.__dict__, "expected_monthly_revenue": 30_000_000})

    assert "기준의 60%" not in _texts(_context(여유))


def test_미확인_금액_칸은_0원이_아니라고_묻는다():
    ctx = _context(unconfirmed=("key_money", "equipment_cost"))

    assert "권리금·설비 비용은 아직 확인하지 않은 값입니다(0원 아님)" in _texts(ctx)


def test_미확인_칸이_없으면_그_질문이_없다():
    assert "확인하지 않은 값" not in _texts(_context())


def test_프리필_월매출을_그대로_쓰면_신규_점포_기준을_묻는다():
    ctx = _context(prefilled=("expected_monthly_revenue",))

    assert "예상 월매출 800만 원은 이 동네 같은 업종의 평균입니다" in _texts(ctx)


def test_월매출을_고쳤으면_그_질문이_없다():
    assert "이 동네 같은 업종의 평균" not in _texts(_context())


def test_프리필_월세를_그대로_쓰면_권역_근사임을_묻는다():
    assert "월세는 권역 평균 기준입니다" in _texts(_context(prefilled=("monthly_rent",)))


def test_월세를_고쳤으면_그_질문이_없다():
    assert "권역 평균 기준" not in _texts(_context())


# --- procedure 4종 ---


def test_사업자등록_여부가_모름이면_묻는다():
    assert "사업자등록 전인지 후인지" in _texts(_context(business_registered=None))


def test_사업자등록_여부를_답했으면_묻지_않는다():
    assert "사업자등록 전인지" not in _texts(_context(business_registered=False))


def test_보증_상태가_모름이면_발급_절차를_묻는다():
    assert "보증서 발급 절차" in _texts(_context(guarantee_status="unknown"))


def test_보증_상태를_알면_묻지_않는다():
    assert "보증서 발급 절차" not in _texts(_context(guarantee_status="in_progress"))


def test_정책자금_확인서_상태가_모름이면_묻는다():
    assert "정책자금 확인서가 필요한지" in _texts(
        _context(policy_confirmation_status="unknown")
    )


def test_정책자금_확인서_상태를_알면_묻지_않는다():
    assert "정책자금 확인서가 필요한지" not in _texts(
        _context(policy_confirmation_status="not_started")
    )


def test_후보_공고는_상위_3건까지만_묻는다():
    ctx = _context(candidate_titles=("공고A", "공고B", "공고C", "공고D"))
    질문 = [q for q in build_questions(ctx) if "해당하는지" in q.text]

    assert len(질문) == 3
    assert "「공고A」에 해당하는지, 은행 대출과 병행 가능한지" == 질문[0].text
    assert "공고D" not in _texts(ctx)


def test_후보_공고가_없으면_그_질문이_없다():
    assert "해당하는지" not in _texts(_context())


# --- 전체 ---


def test_모든_규칙이_해당하면_kind가_gap_assumption_procedure_순으로_묶인다():
    ctx = _context(
        _SHORT_RUNWAY,
        unconfirmed=("key_money",),
        prefilled=("expected_monthly_revenue", "monthly_rent"),
        business_registered=None,
        guarantee_status="unknown",
        policy_confirmation_status="unknown",
        candidate_titles=("공고A", "공고B", "공고C"),
    )
    kinds = _kinds(ctx)

    assert kinds == [KIND_GAP] * 2 + [KIND_ASSUMPTION] * 5 + [KIND_PROCEDURE] * 6


def test_아무것도_해당하지_않으면_빈_목록이다():
    넉넉 = FinanceInput(
        **{**_DEMO.__dict__, "equity": 300_000_000, "desired_loan": 0,
           "expected_monthly_revenue": 30_000_000}
    )

    assert build_questions(_context(넉넉)) == []


def test_모든_질문이_근거를_갖는다():
    ctx = _context(unconfirmed=("key_money",), candidate_titles=("공고A",))

    assert all(q.basis for q in build_questions(ctx))
