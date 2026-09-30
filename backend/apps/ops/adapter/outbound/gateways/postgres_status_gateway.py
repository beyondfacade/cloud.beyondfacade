from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.ops.app.dtos.facility_dto import DatabaseStatusDto, TableSizeDto
from apps.ops.app.ports.output.facility_port import DatabaseStatusPort
from apps.ops.domain.services.collector_catalog import COLLECTORS
from core.matrix.grid_oracle_database_manager import session_scope

_LARGEST_TABLES = 8
# 식별자는 바인딩할 수 없어 SQL에 직접 넣는다 — 카탈로그에 선언된 이름만 허용한다
_ALLOWED = {(c.table, c.time_column) for c in COLLECTORS if c.table}


def _scalar(session: Session, sql: str):
    return session.execute(text(sql)).scalar()


class PostgresStatusGateway(DatabaseStatusPort):
    def read(self) -> DatabaseStatusDto:
        with session_scope() as session:
            largest = session.execute(
                text(
                    """
                    select c.relname, pg_total_relation_size(c.oid), greatest(c.reltuples, 0)::bigint
                    from pg_class c join pg_namespace n on n.oid = c.relnamespace
                    where n.nspname = 'public' and c.relkind = 'r'
                    order by pg_total_relation_size(c.oid) desc
                    limit :limit
                    """
                ),
                {"limit": _LARGEST_TABLES},
            )
            return DatabaseStatusDto(
                version=_scalar(session, "show server_version"),
                size_bytes=_scalar(session, "select pg_database_size(current_database())"),
                connections=_scalar(
                    session, "select count(*) from pg_stat_activity where datname = current_database()"
                ),
                max_connections=int(_scalar(session, "show max_connections")),
                alembic_revision=_scalar(session, "select version_num from alembic_version limit 1"),
                pgvector_version=_scalar(session, "select extversion from pg_extension where extname = 'vector'"),
                largest_tables=[TableSizeDto(*row) for row in largest],
            )

    def table_stats(self, table: str, time_column: str | None) -> tuple[int | None, datetime | None]:
        if (table, time_column) not in _ALLOWED:
            raise ValueError(f"카탈로그에 없는 테이블: {table}.{time_column}")
        with session_scope() as session:
            rows = session.execute(
                text("select greatest(reltuples, 0)::bigint from pg_class where relname = :t and relkind = 'r'"),
                {"t": table},
            ).scalar()
            if rows is None:
                return None, None
            latest = session.execute(text(f'select max("{time_column}") from "{table}"')).scalar() if time_column else None
            return rows, latest
