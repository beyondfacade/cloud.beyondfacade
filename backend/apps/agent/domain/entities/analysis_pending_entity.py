from dataclasses import dataclass
from datetime import datetime, timedelta

# 대기 분석의 수명 — POST 뒤 브라우저가 곧바로 SSE를 연다(보통 몇 초). 30분이 지나도 안 열린 주문은
# 버려진 것(탭 닫힘·서버 재시작 중 끊김)으로 보고 없는 것으로 친다. 지우는 일은 다음 save가 맡는다(크론 없음).
PENDING_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class PendingAnalysis:
    """POST /analysis로 받아 SSE가 열리기를 기다리는 분석 주문 — 워커가 여럿이어도 같은 장부를 본다."""

    analysis_id: str
    region_code: str
    industry_id: str
    question: str | None
    model: str
    budget: int | None
    created_at: datetime
