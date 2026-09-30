"""Driven Adapter — shock BC 유사 사례 UseCase를 리포트 facts dict로 옮긴다 (cross-BC 접근은 여기서만)."""

import json
from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import EventAnalogFactsPort
from apps.shock.dependencies.event_analog_dependencies import get_event_analog_use_case

class EventAnalogFactsGateway(EventAnalogFactsPort):
    def analogs(self, industry_id: str, question: str | None, region_code: str | None = None) -> dict:
        report = get_event_analog_use_case().analogs(industry_id, question, region_code)
        # 날짜를 ISO 문자열로 — facts는 SSE·LLM 메시지로 그대로 직렬화된다
        return json.loads(json.dumps(asdict(report), default=lambda value: value.isoformat()))
