"""Driven Port — Agent가 LLM 프로바이더에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class LLMToolSpec:
    """도구 정의 — 프로바이더 중립."""

    name: str
    description: str
    input_schema: dict


@dataclass
class LLMToolCall:
    """LLM이 요청한 도구 호출."""

    tool_name: str
    arguments: dict


@dataclass
class LLMUsage:
    """토큰 사용량."""

    input_tokens: int
    output_tokens: int


@dataclass
class LLMTurn:
    """한 턴 응답: text 또는 tool_calls (둘 다 가능)."""

    text: str
    tool_calls: list[LLMToolCall]
    usage: LLMUsage


@dataclass
class LLMStreamEvent:
    """스트림 조각 1건 — `kind`로 갈린다 (설계서 §3-4).

    - `text`: 본문 조각. 도착하는 대로 여러 번 온다.
    - `tool_calls`: 그 턴의 도구 호출 전량. 턴 끝에 **정확히 한 번**(없으면 빈 목록) 온다.
    - `usage`: 그 턴의 토큰 사용량. 턴 끝에 한 번 온다.
    """

    kind: str
    text: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    usage: LLMUsage | None = None


class LLMGatewayPort(ABC):
    """LLM 게이트웨이 포트 — 도구 호출이 가능한 채팅 한 턴."""

    model_name: str

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""

    @abstractmethod
    def stream(self, messages: list[dict], tools: list[LLMToolSpec]) -> Iterator[LLMStreamEvent]:
        """같은 한 턴을 조각으로 흘린다 — 본문 조각 여러 건 → tool_calls 1건 → usage 1건."""


class RegionFactsPort(ABC):
    """Driven Port — Agent 도구가 필요로 하는 타 BC 사실 조회 (cross-BC 접근은 구현체 안에서만)."""

    @abstractmethod
    def metrics_history(self, region_code: str, industry_id: str) -> list[dict]:
        """행정동×업종의 연도별 지표 전량 — 추세선의 재료다(점포수·개폐업 수·폐업률·성장률)."""

    @abstractmethod
    def summary(self, region_code: str, industry_id: str) -> dict:
        """사이드패널 카드와 동일한 마스터 요약(fact 카드 목록) + 동 이름·업종명."""

    @abstractmethod
    def population(self, region_code: str) -> dict:
        """최신 기간의 연령 분포 + 학령(5~19세) 인구 합계."""

    @abstractmethod
    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        """업종 필터(선택) 충격 이벤트 목록."""

    @abstractmethod
    def neighborhood_profile(self, region_code: str) -> dict:
        """최신 분기 동네 프로필 + reasons·conditions 절이 쓰는 지표·시간대 재료.

        프론트 `RegionProfile` 키를 그대로 싣는다 — 없으면 {"available": False, "reason": ...}.
        """

    @abstractmethod
    def hour_gap(self, region_code: str, industry_id: str) -> dict:
        """최신 분기 시간대 어긋남 6구간 — 자료가 없으면 {"available": False, "reason": ...}."""

    @abstractmethod
    def commerce_change_detail(self, region_code: str) -> dict:
        """최신 분기 상권 변화 지표 + 같은 분기 서울 평균 — 없으면 {"available": False, "reason": ...}."""


class FundingFactsPort(ABC):
    """Driven Port — 정책자금 후보 공고 조회 (결정론 필터, 설계서 §3).

    RAG `search_funding`(유사도)과 역할이 다르다 — 이쪽은 지역·대상·마감으로 거르는 규칙이다.
    """

    @abstractmethod
    def candidates(
        self,
        industry_id: str | None,
        external_funding_need: int | None,
        stage: str | None,
        region_code: str | None = None,
        question: str | None = None,
    ) -> dict:
        """서울/전국 미만료 공고 상위 8건 + 요청 값 되돌림. 자격 확정이 아니다.

        `region_code`(동)를 주면 다른 구 전용 공고는 뺀다. `question`이 있으면 규칙을 통과한 후보를
        질문과 가까운 순으로 고른다 — 어느 순서인지는 `order`("relevance"|"deadline")로 돌려준다.
        """


class VerdictFactsPort(ABC):
    """Driven Port — verdict BC의 판정 카드·대안 조회 (cross-BC 접근은 구현체 안에서만).

    판정 없음·판정 대상 아님은 예외가 아니라 `{"available": False, "reason": ...}` 값으로 돌려준다 —
    LLM이 "판정 없음"을 이유와 함께 그대로 옮겨 쓸 수 있어야 한다 (설계서 §5-2).
    """

    @abstractmethod
    def verdict(self, region_code: str, industry_id: str) -> dict:
        """판정 카드 전 필드 — 등급·신호 5개(근거·백분위·참고 여부)·산출일."""

    @abstractmethod
    def alternatives(self, region_code: str, industry_id: str) -> dict:
        """대안 두 축 — 같은 동네의 다른 업종, 같은 업종의 다른 동네."""


class EventAnalogFactsPort(ABC):
    """Driven Port — shock BC의 유사 사례(진행 중·질문 속 이벤트 유형의 지난 사례와 업종 변동폭).

    유형 단서가 질문에 있으므로 `RegionFactsPort`(동·업종 사실)와 따로 둔다(ISP).
    """

    @abstractmethod
    def analogs(self, industry_id: str, question: str | None) -> dict:
        """유형·진행 중 이벤트·지난 사례(창별 대상 업종 변동폭·강세/약세 업종)·해석 주의사항."""


class FinanceFactsPort(ABC):
    """Driven Port — finance BC의 자금 계획 프리필(동·업종 점포당 월 평균 매출·권역 임대료·공시 금리).

    질문 직접 답의 예산·대출 근거로 쓴다 (설계서 2026-10-05-question-answer §7).
    """

    @abstractmethod
    def prefill(self, region_code: str, industry_id: str) -> dict:
        """{"available": True, "expected_monthly_revenue"|"rent_per_m2"|"loan_rate": {value, unit, basis, caveat}}."""


class QuestionBudgetPort(ABC):
    """Driven Port — 질문 속 금액(원). 의도 관문과 같은 규칙을 쓴다."""

    @abstractmethod
    def parse(self, question: str) -> int | None:
        """금액이 없으면 None."""


class NewsLinksPort(ABC):
    """Driven Port — news BC의 최근 기사 원문 링크. 네이버 검색 결과라 링크로만 보여 주고 LLM에 넣지 않는다
    (검색 API 특약 2.2·2.3). 발췌는 싣지 않는다."""

    @abstractmethod
    def mentioning(self, name: str, limit: int) -> list[dict]:
        """제목·발췌에 name이 나온 보관 기간(21일) 안 기사, 최신순 — {title, url, published_at(YYYY-MM-DD), press}."""


class RegionalEventsPort(ABC):
    """Driven Port — shock BC의 지역 사건(정비사업 이주·착공, 대규모점포 개설·폐업, 대단지 입주). 서울 열린데이터광장 원천."""

    @abstractmethod
    def for_region(self, region_code: str) -> list[dict]:
        """행정동 1곳의 지역 사건, 최근 것 먼저 — {start_date(YYYY-MM-DD), end_date, name, source, source_url}."""
