"""크론 수집기 카탈로그 — scripts/*.sh 러너와 짝. 주기는 각 스크립트 머리 주석의 크론 일정과 같다."""

from dataclasses import dataclass
from datetime import datetime, timedelta

_LATE_FACTOR = 1.5  # 한 주기 + 반 주기까지는 정상 (크론 시각 직전 조회 대비)


@dataclass(frozen=True)
class Collector:
    key: str
    label: str
    schedule: str
    interval: timedelta
    log_file: str  # 저장소 logs/ 아래
    table: str | None = None  # 행 수·최신 시각을 볼 대표 테이블
    time_column: str | None = None


COLLECTORS: tuple[Collector, ...] = (
    Collector("news-poller", "뉴스 폴링", "매시", timedelta(hours=1), "news-poller.log", "news_article", "published_at"),
    Collector("store-collector", "인허가 점포", "매일 04:20", timedelta(days=1), "store-collector.log", "store", "source_updated_at"),
    Collector("funding-collector", "정책자금 공고", "매일 05:10", timedelta(days=1), "funding-collector.log", "funding_program", "posted_at"),
    Collector("rag-indexer", "RAG 색인", "매일 05:50", timedelta(days=1), "rag-indexer.log", "rag_chunk", "published_at"),
    Collector("interest-rate-collector", "금리·임대동향", "매주 월 05:20", timedelta(weeks=1), "interest-rate-collector.log", "interest_rate"),
    Collector("childcare-collector", "어린이집", "매주 월 05:30", timedelta(weeks=1), "childcare-collector.log", "childcare_center"),
    Collector("convenience-collector", "편의점", "매주 월 05:40", timedelta(weeks=1), "convenience-collector.log", "convenience_store"),
    Collector("host-metrics-sampler", "설비 지표 표본", "매분", timedelta(minutes=1), "host-metrics-sampler.log", "host_metric_sample", "sampled_at"),
    Collector("admin-housekeeping", "관리자 기록 정리", "매일 03:30", timedelta(days=1), "admin-housekeeping.log"),
)
COLLECTOR_BY_KEY: dict[str, Collector] = {collector.key: collector for collector in COLLECTORS}


def collector_status(last_run_at: datetime | None, interval: timedelta, now: datetime) -> str:
    if last_run_at is None:
        return "missing"
    return "ok" if now - last_run_at <= interval * _LATE_FACTOR else "late"
