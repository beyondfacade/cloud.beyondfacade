"""네이버 검색 결과 정리 — RAG 뉴스 청크 삭제, 저장 리포트의 뉴스 인용·코드가 쓴 뉴스 줄 제거

Revision ID: a9e4c2b7d153
Revises: c7a3f1e8d204
Create Date: 2026-10-06 00:00:00.000000

네이버 검색 API 특약 2.3(저장·AI 입력 금지)·2.4(서버 보관 최대 21일) 대응 (BE v0.83.0).
앞으로는 코드가 막는다 — 뉴스 색인 중단, 리포트 본문·LLM 입력에서 뉴스 제외, 인용 미저장,
news_article은 수집기가 21일 지난 기사를 지운다. 이 마이그레이션은 이미 쌓인 것을 한 번 지운다.

- rag_chunk의 news 청크 전부
- analysis_report.citations_json → '[]' (인용은 뉴스 링크뿐이었다)
- analysis_report.report_md에서 코드가 쓴 뉴스 줄: "[참고 신호] ○○ 이름이 나온 최근 뉴스: …" 줄과
  유사 사례 문단 끝의 "[참고 신호] 최근 N일 … 관련 뉴스는 N건입니다/같은 조치 소식은 없습니다" ·
  "[참고 신호] ○○ 최근 소식은 확인하지 못했습니다." 꼬리. 옛 LLM 해석이 기사를 풀어 쓴 문장은 패턴으로
  가릴 수 없어 여기서 다루지 않는다.

되돌릴 수 없다(지운 데이터) — downgrade는 아무것도 하지 않는다.
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9e4c2b7d153"
down_revision: Union[str, Sequence[str], None] = "c7a3f1e8d204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEWS_LINE = re.compile(r"\n*\[참고 신호\] [^\n]*이름이 나온 최근 뉴스:[^\n]*")
# 뉴스 문장 하나(첫 "다.")까지만 — 옛 LLM 해석은 같은 줄 뒤에 다른 말을 이어 썼다
_ANALOG_NEWS_TAIL = re.compile(r" ?\[참고 신호\] (?:최근 \d+일 [^\n\[]*?다\.|[^ \n]+ 최근 소식은 확인하지 못했습니다\.)")


def strip_news(report_md: str) -> str:
    return _ANALOG_NEWS_TAIL.sub("", _NEWS_LINE.sub("", report_md))


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM rag_chunk WHERE source_type = 'news'"))
    bind.execute(sa.text("UPDATE analysis_report SET citations_json = '[]' WHERE citations_json <> '[]'"))
    rows = bind.execute(sa.text("SELECT id, report_md FROM analysis_report WHERE report_md LIKE '%[참고 신호]%'")).all()
    for report_id, report_md in rows:
        cleaned = strip_news(report_md)
        if cleaned != report_md:
            bind.execute(
                sa.text("UPDATE analysis_report SET report_md = :md WHERE id = :id"), {"md": cleaned, "id": report_id}
            )


def downgrade() -> None:
    pass
