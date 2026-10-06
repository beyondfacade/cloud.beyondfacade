"""옛 LLM 해석이 네이버 뉴스를 풀어 쓴 저장 리포트 본문 비우기

Revision ID: b3f7d1e9a264
Revises: a9e4c2b7d153
Create Date: 2026-10-06 00:00:00.000000

네이버 검색 API 특약 2.3·2.4 — 검색 결과의 가공·파생물도 21일 넘게 저장할 수 없다 (BE v0.83.1, 사용자 결정).
a9e4c2b7d153이 코드가 쓴 뉴스 줄은 지웠지만, v0.68.0 전 LLM이 리포트 전체를 쓰던 때(gemini-2.5-flash,
2026-09-24 ~ 10-02)의 해석은 기사 제목·내용을 문장 속에 풀어 써서 패턴으로 골라 지울 수 없다.
본문에 "뉴스·기사·보도"가 나오는 리포트(적용 시점 39건, 전부 그 시기 것)의 report_md를 표시 문구로 바꾼다.

행은 지우지 않는다 — llm_usage.analysis_id(NOT NULL FK)가 참조하고, 관리자 사용량 통계가 그 행을 쓴다.
되돌릴 수 없다 — downgrade는 아무것도 하지 않는다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3f7d1e9a264"
down_revision: Union[str, Sequence[str], None] = "a9e4c2b7d153"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CLEARED = "(본문 삭제 — 네이버 뉴스 검색 결과를 풀어 쓴 옛 해석이라 이용조건에 따라 지웠습니다. 2026-10-06)"


def upgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE analysis_report SET report_md = :cleared WHERE report_md ~ '뉴스|기사|보도'"),
        {"cleared": _CLEARED},
    )


def downgrade() -> None:
    pass
