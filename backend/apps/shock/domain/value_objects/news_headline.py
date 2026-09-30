"""뉴스 헤드라인 VO — 지금 상황 확인용. 제목·시각·링크만 담는다 (본문 저장 금지, 저작권 경계)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsHeadline:
    title: str
    published_at: datetime
    url: str
