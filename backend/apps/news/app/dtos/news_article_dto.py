from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsArticleDto:
    article_id: str
    title: str
    description: str
    published_at: datetime
    url: str
    matched_keyword: str
    press: str | None = None
    region_code: str | None = None
