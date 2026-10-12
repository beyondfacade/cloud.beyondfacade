from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatConsultation:
    """일반 회원이 산 전문가 상담 시간 — 끝나기 전까지 그 전문가는 '대화 중'이다."""

    viewer_id: int
    expert_id: int
    hours: int
    price: int  # 원
    started_at: datetime
    ends_at: datetime
    id: int | None = None
