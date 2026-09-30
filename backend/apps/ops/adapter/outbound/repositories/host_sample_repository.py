from dataclasses import asdict, fields
from datetime import datetime, timedelta

from sqlalchemy import delete, func, literal, select
from sqlalchemy.dialects.postgresql import insert

from apps.ops.adapter.outbound.orms.host_metric_sample_orm import HostMetricSampleOrm
from apps.ops.app.ports.output.host_sample_port import HostSampleRepositoryPort
from apps.ops.domain.entities.host_sample_entity import HostSample
from core.matrix.grid_oracle_database_manager import session_scope

_METRICS = tuple(f.name for f in fields(HostSample) if f.name != "sampled_at")
_ORIGIN = datetime.fromisoformat("2000-01-01T00:00:00+00:00")  # date_bin 기준점 — 버킷 경계를 고정


class SqlAlchemyHostSampleRepository(HostSampleRepositoryPort):
    def add(self, sample: HostSample) -> None:
        values = asdict(sample)
        statement = insert(HostMetricSampleOrm).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[HostMetricSampleOrm.sampled_at], set_={name: values[name] for name in _METRICS}
        )
        with session_scope() as session:
            session.execute(statement)

    def series(self, since: datetime, bucket_seconds: int) -> list[HostSample]:
        bucket = func.date_bin(
            literal(timedelta(seconds=bucket_seconds)), HostMetricSampleOrm.sampled_at, literal(_ORIGIN)
        ).label("bucket")
        columns = [func.avg(getattr(HostMetricSampleOrm, name)).label(name) for name in _METRICS]
        query = (
            select(bucket, *columns)
            .where(HostMetricSampleOrm.sampled_at >= since)
            .group_by(bucket)
            .order_by(bucket)
        )
        with session_scope() as session:
            return [
                HostSample(
                    sampled_at=row.bucket,
                    **{name: round(float(v), 1) if (v := getattr(row, name)) is not None else None for name in _METRICS},
                )
                for row in session.execute(query)
            ]

    def delete_before(self, cutoff: datetime) -> int:
        with session_scope() as session:
            return session.execute(
                delete(HostMetricSampleOrm).where(HostMetricSampleOrm.sampled_at < cutoff)
            ).rowcount
