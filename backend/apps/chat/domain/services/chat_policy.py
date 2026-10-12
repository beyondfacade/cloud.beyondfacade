"""채팅 메시지 규칙 — 본문 길이, 도배 방지, 답장 미리보기."""

from datetime import datetime, timedelta

MAX_BODY_LENGTH = 500
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = timedelta(seconds=10)
_PREVIEW_LENGTH = 80


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
