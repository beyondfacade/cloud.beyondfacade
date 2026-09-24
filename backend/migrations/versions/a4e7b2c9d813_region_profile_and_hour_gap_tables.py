"""파생 지표 2종 테이블 + cafe·hair_salon 업종 매핑 보정

Revision ID: a4e7b2c9d813
Revises: f3c9a1d47b62
Create Date: 2026-09-23 00:00:00.000000

동네 맥락·매출 원자료 999만 행에서 화면이 읽을 수 있는 것을 뽑는 파생 계층이다
(설계서 `docs/superpowers/specs/2026-09-23-region-profile-design.md` §4).

- `region_profile_quarter`는 판정과 근거 수치를 함께 넓은 형태로 둔다. 값 컬럼이 반복 그룹이
  아니라 서로 다른 측정값이라 긴 형태로 내리면 "직장비와 주말지수를 같이"가 self-join이 된다
- `region_industry_hour_gap_quarter`는 구간을 행으로 편다. 단일 점수로 뭉개면 "어느 구간에서
  어긋나는가"를 말할 수 없다
- 업종 매핑 4행 추가는 교차검증(`2026-09-23-commerce-crossvalidation.md` §3-2)의 결론이다.
  `cafe`에 패스트푸드·분식, `hair_salon`에 네일·피부를 더해야 우리 인허가 모집단과 맞는다.
  시드에 반영이 안 된 채로 두면 두 업종의 시간대 매출이 조용히 과소 집계된다

autogenerate를 쓰지 않았다 — 이 브랜치의 alembic head와 실DB 리비전이 갈라져 있어
(feature/analysis-api의 a1b2c3d4e5f6·b2c3d4e5f6a7가 DB에만 적용된 상태) 무관한 삭제를 오탐한다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4e7b2c9d813"
down_revision: Union[str, Sequence[str], None] = "f3c9a1d47b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 교차검증 §3-2 — 1:1 시드에서 빠진 서브카테고리
_ADDED_SOURCE_CODES: tuple[tuple[str, str], ...] = (
    ("cafe", "CS100006"),  # 패스트푸드점
    ("cafe", "CS100008"),  # 분식전문점
    ("hair_salon", "CS200029"),  # 네일숍
    ("hair_salon", "CS200030"),  # 피부관리실
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "region_profile_quarter",
        sa.Column("region_code", sa.String(), nullable=False),
        sa.Column("year_quarter", sa.String(length=5), nullable=False),
        sa.Column("neighborhood_type", sa.String(length=12), nullable=False),
        sa.Column("type_reason", sa.Text(), nullable=False),
        sa.Column("time_label", sa.String(length=8), nullable=True),
        sa.Column("peak_block", sa.String(length=8), nullable=True),
        sa.Column("trough_block", sa.String(length=8), nullable=True),
        sa.Column("worker_resident_ratio", sa.Float(), nullable=True),
        sa.Column("weekend_index", sa.Float(), nullable=True),
        sa.Column("night_index", sa.Float(), nullable=True),
        sa.Column("footfall_20s_share", sa.Float(), nullable=True),
        sa.Column("fnb_share", sa.Float(), nullable=True),
        sa.Column("facility_total", sa.Integer(), nullable=True),
        sa.Column("resident_total", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["region_code"], ["region.region_code"]),
        sa.PrimaryKeyConstraint("region_code", "year_quarter"),
    )
    op.create_index(
        "ix_region_profile_quarter_quarter_type",
        "region_profile_quarter",
        ["year_quarter", "neighborhood_type"],
        unique=False,
    )
    op.create_table(
        "region_industry_hour_gap_quarter",
        sa.Column("region_code", sa.String(), nullable=False),
        sa.Column("industry_id", sa.String(), nullable=False),
        sa.Column("year_quarter", sa.String(length=5), nullable=False),
        sa.Column("hour_band", sa.String(length=5), nullable=False),
        sa.Column("footfall_intensity", sa.Float(), nullable=False),
        sa.Column("sales_intensity", sa.Float(), nullable=False),
        sa.Column("gap", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["industry_id"], ["industry.industry_id"]),
        sa.ForeignKeyConstraint(["region_code"], ["region.region_code"]),
        sa.PrimaryKeyConstraint("region_code", "industry_id", "year_quarter", "hour_band"),
    )
    op.create_index(
        "ix_region_industry_hour_gap_quarter_region_quarter",
        "region_industry_hour_gap_quarter",
        ["region_code", "year_quarter"],
        unique=False,
    )
    # 빈 DB(테스트 DB)엔 industry 행이 없어 FK 위반으로 전체 롤백된다 — 마스터는 seed_master CLI 몫이라 건너뛴다
    if op.get_bind().execute(sa.text("select count(*) from industry")).scalar() == 0:
        return
    op.bulk_insert(
        sa.table(
            "industry_source_code",
            sa.column("industry_id", sa.String),
            sa.column("source_system", sa.String),
            sa.column("code", sa.String),
        ),
        [
            {"industry_id": industry_id, "source_system": "seoul_commercial", "code": code}
            for industry_id, code in _ADDED_SOURCE_CODES
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM industry_source_code WHERE source_system = 'seoul_commercial' "
        "AND code IN ('CS100006', 'CS100008', 'CS200029', 'CS200030')"
    )
    op.drop_index(
        "ix_region_industry_hour_gap_quarter_region_quarter",
        table_name="region_industry_hour_gap_quarter",
    )
    op.drop_table("region_industry_hour_gap_quarter")
    op.drop_index("ix_region_profile_quarter_quarter_type", table_name="region_profile_quarter")
    op.drop_table("region_profile_quarter")
