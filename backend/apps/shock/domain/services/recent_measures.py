"""최근 조치 기사 — 지난 사례의 결론이 지금도 해당하는지 가리는 근거.

기사 수는 신호가 못 된다: "감염병 유행"으로 찾으면 평소에도 30일 치가 100건 넘게 찬다(예방접종 안내 등).
그래서 영업을 막는 조치 단어가 **제목에** 든 기사만 센다 — 평소엔 0건이고 유행기엔 쏟아진다.
"""

from collections.abc import Iterable
from datetime import date

from apps.shock.domain.value_objects.news_headline import NewsHeadline

NEWS_DAYS = 30
HEADLINES_SHOWN = 3


def _squash(text: str) -> str:
    return "".join(text.split())


def measure_headlines(
    headlines: Iterable[NewsHeadline], keywords: Iterable[str], since: date
) -> list[NewsHeadline]:
    """기간 안에 제목에 조치 단어가 든 기사 — 띄어쓰기 무시, 같은 링크는 한 번, 최신순."""
    squashed = [_squash(k) for k in keywords]
    unique: dict[str, NewsHeadline] = {}
    for headline in headlines:
        title = _squash(headline.title)
        if headline.published_at.date() >= since and any(k in title for k in squashed):
            unique.setdefault(headline.url, headline)
    return sorted(unique.values(), key=lambda h: h.published_at, reverse=True)
