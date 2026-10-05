"""Driven Adapter — 의도 관문의 금액 규칙 재사용 (cross-BC 접근은 이 파일 안에서만)."""

from apps.agent.app.ports.output.agent_port import QuestionBudgetPort
from apps.intent.domain.services.extractors import parse_budget


class QuestionBudgetGateway(QuestionBudgetPort):
    def parse(self, question: str) -> int | None:
        return parse_budget(question)
