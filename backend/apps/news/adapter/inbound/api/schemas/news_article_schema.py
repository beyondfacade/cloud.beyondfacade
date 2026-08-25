from datetime import datetime

from pydantic import BaseModel


class NewsArticleResponse(BaseModel):
    article_id: str
    title: str
    description: str
    published_at: datetime
    url: str
    matched_keyword: str
    press: str | None = None
    region_code: str | None = None
