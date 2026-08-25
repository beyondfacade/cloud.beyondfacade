from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsArticle:
    """뉴스 기사 — 제목·발췌·링크만 보유 (본문 저장 금지, 저작권 경계)."""

    article_id: str
    title: str
    description: str
    published_at: datetime
    url: str
    matched_keyword: str
    press: str | None = None  # 네이버 응답에 언론사명 없음 — 타 소스 대비 nullable
    region_code: str | None = None
