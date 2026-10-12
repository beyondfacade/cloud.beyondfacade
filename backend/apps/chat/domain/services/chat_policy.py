"""채팅 메시지 규칙 — 본문 길이, 도배 방지, 답장 미리보기, 1:1 상대, 전문가 상담 상태."""

from datetime import datetime, timedelta

MAX_BODY_LENGTH = 500
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = timedelta(seconds=10)
_PREVIEW_LENGTH = 80
DIRECT_OPENER_ROLE = "viewer"
DIRECT_PARTNER_ROLE = "expert"
CONSULTATION_HOURS = (1, 2, 3)


def expert_status(expert_id: int, member_id: int, holders: dict[int, int]) -> str:
    """available(대화 가능) · busy(다른 회원이 산 상담 중) · mine(내가 산 상담 중)."""
    holder = holders.get(expert_id)
    if holder is None:
        return "available"
    return "mine" if holder == member_id else "busy"


def can_open_direct(opener_role: str, peer_role: str) -> bool:
    """1:1은 일반 회원이 전문가에게만 건다 — 전문가는 열린 방에서 답만 한다."""
    return opener_role == DIRECT_OPENER_ROLE and peer_role == DIRECT_PARTNER_ROLE


def can_talk_direct(role: str, partner_role: str) -> bool:
    """이미 열린 1:1도 지금 일반↔전문가 사이일 때만 보낸다 — 등급이 바뀌면 더 못 보낸다."""
    return {role, partner_role} == {DIRECT_OPENER_ROLE, DIRECT_PARTNER_ROLE}


def clean_body(body: str) -> str | None:
    """보낼 수 있는 본문이면 앞뒤 공백을 뗀 글, 비었거나 너무 길면 None."""
    text = body.strip()
    if not text or len(text) > MAX_BODY_LENGTH:
        return None
    return text


def rate_window_start(now: datetime) -> datetime:
    """이 시각 이후 같은 사람이 RATE_LIMIT_COUNT개를 이미 보냈으면 도배로 본다."""
    return now - RATE_LIMIT_WINDOW


def reply_preview(body: str) -> str:
    first_line = body.split("\n", 1)[0]
    return first_line if len(first_line) <= _PREVIEW_LENGTH else first_line[:_PREVIEW_LENGTH] + "…"
