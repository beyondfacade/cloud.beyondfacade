"""확인할 질문 초안 — 계획의 수치에서 결정론으로 만든다 (설계서 §4).

상담의 결과물은 상품 목록이 아니라 **무엇을 물어볼지**다. LLM을 쓰지 않는다 — 질문은 계획에 실제로
들어 있는 수치에서만 나와야 하고, 근거(`basis`)가 어느 값에서 나왔는지 말할 수 있어야 한다.

규칙은 `if/elif` 체인이 아니라 **규칙 객체 리스트**다(Chain of Responsibility, CLAUDE.md §5).
각 규칙은 해당할 때만 질문을 낸다. 후보 공고 규칙만 최대 3개를 내고 나머지는 0 또는 1개다.

**서버는 초안만 준다.** 사용자가 편집·삭제·추가하는 것이 전제다.

경계 하나: 후보 공고 제목은 요청으로 받는다. finance BC가 funding BC를 직접 읽지 않는다 — 화면이
`GET /funding/candidates` 결과를 실어 보낸다. 두 BC를 묶으면 계획 계산이 공고 적재에 묶인다.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from apps.finance.domain.services.engine import FinanceInput, FinanceResult

KIND_GAP = "gap"
KIND_ASSUMPTION = "assumption"
KIND_PROCEDURE = "procedure"

STATUS_UNKNOWN = "unknown"

_WON_PER_MANWON = 10_000
_PESSIMISTIC = "비관"
_RUNWAY_FLOOR_MONTHS = 6
_MAX_CANDIDATE_QUESTIONS = 3

# 미확인 금액 필드 → 화면 라벨. 폼의 라벨과 같은 말을 써야 사용자가 어느 칸인지 안다
AMOUNT_FIELD_LABELS: dict[str, str] = {
    "deposit": "보증금",
    "key_money": "권리금",
    "interior_cost": "인테리어 비용",
    "equipment_cost": "설비 비용",
    "monthly_rent": "월세",
    "monthly_payroll": "월 인건비",
    "monthly_insurance": "월 보험료",
    "equity": "자기자본",
    "desired_loan": "희망 대출금",
    "expected_monthly_revenue": "예상 월매출",
}


def topic_particle(word: str) -> str:
    """은/는 — 마지막 글자가 한글이고 받침이 있으면 은. intent BC와 같은 규칙(BC별 사본)."""
    if not word:
        return "는"
    last = word[-1]
    if "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28:
        return "은"
    return "는"


def to_manwon(won: int | float) -> str:
    """원 → 만원 표기. 화면이 만원 단위로 보여주므로 질문도 같은 단위로 쓴다."""
    return f"{round(won / _WON_PER_MANWON):,}"


@dataclass(frozen=True)
class Question:
    text: str
    basis: str  # 어느 수치에서 나왔는지 한 줄
    kind: str  # gap | assumption | procedure


@dataclass(frozen=True)
class QuestionContext:
    """질문 생성 입력 — 계획 입력·서버가 다시 계산한 결과·확인 상태."""

    finance: FinanceInput
    result: FinanceResult
    unconfirmed: tuple[str, ...] = ()
    # 프리필 값을 사용자가 한 번도 고치지 않은 필드 — 화면의 `touched` 여집합
    prefilled: tuple[str, ...] = ()
    business_registered: bool | None = None
    guarantee_status: str = STATUS_UNKNOWN
    policy_confirmation_status: str = STATUS_UNKNOWN
    candidate_titles: tuple[str, ...] = ()

    def scenario(self, name: str):
        return next((s for s in self.result.scenarios if s.name == name), None)


class QuestionRule(ABC):
    @abstractmethod
    def ask(self, ctx: QuestionContext) -> list[Question]:
        """해당하면 질문을, 아니면 빈 리스트를 반환해 다음 규칙에 넘긴다."""


class ExternalFundingNeedRule(QuestionRule):
    """조달 필요액이 남아 있으면 — 헤드라인 질문. 부족액 0원과 무관하게 묻는다."""

    def ask(self, ctx):
        need = ctx.result.external_funding_need
        if need <= 0:
            return []
        return [
            Question(
                text=f"자기자본 외 {to_manwon(need)}만 원을 어떤 경로(보증·대출·정책자금)로 나눠 조달할 수 있는지",
                basis=f"자기자본 외 조달 필요 {need:,}원 > 0",
                kind=KIND_GAP,
            )
        ]


class FundingGapRule(QuestionRule):
    """희망대출을 다 받아도 남는 돈이 있으면."""

    def ask(self, ctx):
        gap = ctx.result.funding_gap
        if gap <= 0:
            return []
        return [
            Question(
                text=(
                    f"희망대출 {to_manwon(ctx.finance.desired_loan)}만 원이 승인돼도 "
                    f"{to_manwon(gap)}만 원이 남습니다. 추가 조달 또는 비용 축소 중 무엇이 현실적인지"
                ),
                basis=f"희망대출 반영 후 부족액 {gap:,}원 > 0",
                kind=KIND_GAP,
            )
        ]


class DesiredLoanTermsRule(QuestionRule):
    """희망대출을 넣었으면 그 조건을 묻는다 — 계산은 공시 평균으로 했다."""

    def ask(self, ctx):
        loan = ctx.finance.desired_loan
        if loan <= 0:
            return []
        rate_pct = round(ctx.finance.loan_rate * 100, 2)
        return [
            Question(
                text=(
                    f"희망대출 {to_manwon(loan)}만 원의 예상 금리·기간·상환 방식. "
                    f"계산은 공시 평균 {rate_pct}%로 했습니다"
                ),
                basis=f"희망대출 {loan:,}원 · 적용 금리 {rate_pct}%",
                kind=KIND_ASSUMPTION,
            )
        ]


class PessimisticRunwayRule(QuestionRule):
    """비관 시나리오에서 6개월을 못 버티면.

    런웨이가 None인 경우는 두 가지다 — 영업이익이 양수라 버틸 필요가 없거나, 가용현금이 0 이하라
    계산 자체가 안 되거나. 후자는 더 나쁘지만 "몇 개월"을 말할 수 없어 여기서 묻지 않는다.
    """

    def ask(self, ctx):
        scenario = ctx.scenario(_PESSIMISTIC)
        months = scenario.runway_months if scenario else None
        if months is None or months >= _RUNWAY_FLOOR_MONTHS:
            return []
        return [
            Question(
                text=f"매출이 기준의 60%일 때 {months}개월 버팁니다. 그 경우 대비책을 상담에서 물어볼지",
                basis=f"비관 시나리오 런웨이 {months}개월 < {_RUNWAY_FLOOR_MONTHS}개월",
                kind=KIND_ASSUMPTION,
            )
        ]


class UnconfirmedAmountsRule(QuestionRule):
    """한 번도 입력하지 않은 금액 칸 — 0원이 아니라 '모름'이다 (대구 §4-2)."""

    def ask(self, ctx):
        labels = [AMOUNT_FIELD_LABELS[f] for f in ctx.unconfirmed if f in AMOUNT_FIELD_LABELS]
        if not labels:
            return []
        joined = "·".join(labels)
        return [
            Question(
                text=(
                    f"{joined}{topic_particle(joined)} 아직 확인하지 않은 값입니다(0원 아님). "
                    "견적을 받아야 하는지"
                ),
                basis=f"미확인 금액 필드 {len(labels)}개: {joined}",
                kind=KIND_ASSUMPTION,
            )
        ]


class PrefilledRevenueRule(QuestionRule):
    """실측 프리필 월매출을 그대로 쓰고 있으면 — 신규 점포는 평균 아래서 시작한다."""

    def ask(self, ctx):
        if "expected_monthly_revenue" not in ctx.prefilled:
            return []
        revenue = ctx.finance.expected_monthly_revenue
        return [
            Question(
                text=(
                    f"예상 월매출 {to_manwon(revenue)}만 원은 이 동네 같은 업종의 평균입니다. "
                    "신규 점포 기준으로 낮춰 잡아야 하는지"
                ),
                basis="예상 월매출이 실측 프리필 값 그대로",
                kind=KIND_ASSUMPTION,
            )
        ]


class PrefilledRentRule(QuestionRule):
    """월세가 권역 근사 그대로면 — 행정동 단위 임대료 자료가 없다."""

    def ask(self, ctx):
        if "monthly_rent" not in ctx.prefilled:
            return []
        return [
            Question(
                text="월세는 권역 평균 기준입니다. 실제 매물 조건으로 다시 계산해야 하는지",
                basis="월세가 권역 임대료 근사 값 그대로",
                kind=KIND_ASSUMPTION,
            )
        ]


class BusinessRegisteredRule(QuestionRule):
    """사업자등록 여부 — 지원 대상이 갈린다. 모름을 '아니오'로 바꾸지 않는다."""

    def ask(self, ctx):
        if ctx.business_registered is not None:
            return []
        return [
            Question(
                text="사업자등록 전인지 후인지에 따라 지원 대상이 달라집니다 — 어느 쪽인지",
                basis="사업자등록 여부 미확인",
                kind=KIND_PROCEDURE,
            )
        ]


class GuaranteeStatusRule(QuestionRule):
    def ask(self, ctx):
        if ctx.guarantee_status != STATUS_UNKNOWN:
            return []
        return [
            Question(
                text="보증기관(서울신용보증재단) 보증서 발급 절차와 소요 기간",
                basis="보증 진행 상태 미확인",
                kind=KIND_PROCEDURE,
            )
        ]


class PolicyConfirmationRule(QuestionRule):
    def ask(self, ctx):
        if ctx.policy_confirmation_status != STATUS_UNKNOWN:
            return []
        return [
            Question(
                text="소상공인 정책자금 확인서가 필요한지, 필요하다면 발급 절차",
                basis="정책자금 확인서 상태 미확인",
                kind=KIND_PROCEDURE,
            )
        ]


class CandidateProgramsRule(QuestionRule):
    """후보 공고는 자격 확정이 아니다 — 해당 여부와 병행 가능성을 묻는다. 상위 3건."""

    def ask(self, ctx):
        return [
            Question(
                text=f"「{title}」에 해당하는지, 은행 대출과 병행 가능한지",
                basis=f"후보 공고 {rank}위",
                kind=KIND_PROCEDURE,
            )
            for rank, title in enumerate(ctx.candidate_titles[:_MAX_CANDIDATE_QUESTIONS], 1)
        ]


# 순서가 곧 화면 순서다 — 돈 이야기(gap) → 가정(assumption) → 절차(procedure)
RULES: tuple[QuestionRule, ...] = (
    ExternalFundingNeedRule(),
    FundingGapRule(),
    DesiredLoanTermsRule(),
    PessimisticRunwayRule(),
    UnconfirmedAmountsRule(),
    PrefilledRevenueRule(),
    PrefilledRentRule(),
    BusinessRegisteredRule(),
    GuaranteeStatusRule(),
    PolicyConfirmationRule(),
    CandidateProgramsRule(),
)


def build_questions(ctx: QuestionContext, rules: Sequence[QuestionRule] = RULES) -> list[Question]:
    return [question for rule in rules for question in rule.ask(ctx)]
