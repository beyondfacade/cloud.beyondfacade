"""뉴스 폴링 수집기 (Driving Adapter, CLI — 크론 주기 실행 대상).

기본 키워드: 서울 25개 자치구명 + "상권" (district 마스터에서 로드).
호출량: 25회/실행 — 시간당 1회 크론 기준 일 600회 (일 한도 25,000회 내).
적재 뒤 게시 21일이 지난 기사를 지운다 (네이버 검색 API 특약 2.4 — 서버 보관 최대 21일).

실행: python -m apps.news.adapter.inbound.cli.news_poller [키워드 ...]
"""

import sys
from datetime import datetime

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.news.adapter.outbound.gateways.naver_news_gateway import NaverNewsGateway
from apps.news.adapter.outbound.repositories.news_article_repository import (
    SqlAlchemyNewsArticleRepository,
)
from apps.news.app.use_cases.news_article_interactor import NewsArticleInteractor
from core.matrix.grid_oracle_database_manager import session_scope


def _default_keywords() -> list[str]:
    with session_scope() as session:
        districts = session.execute(select(DistrictOrm.name).order_by(DistrictOrm.name)).scalars()
        return [f"{name} 상권" for name in districts]


def main(keywords: list[str]) -> None:
    interactor = NewsArticleInteractor(
        repository=SqlAlchemyNewsArticleRepository(),
        gateway=NaverNewsGateway(),
    )
    inserted = interactor.ingest(keywords or _default_keywords())
    purged = interactor.purge(datetime.now())
    print(f"news poller: 신규 {inserted}건 적재, 보관 기한 지난 {purged}건 삭제")


if __name__ == "__main__":
    main(sys.argv[1:])
