"""rag BC의 rag_chunk를 읽기 전용으로 집계한다 (cross-BC 접근은 이 구현체 안에서만)."""

from sqlalchemy import text

from apps.ops.app.dtos.healthcare_dto import EmbedderCountDto, RagSourceStatsDto, RagStatsDto
from apps.ops.app.ports.output.healthcare_port import RagStatsPort
from core.matrix.grid_oracle_database_manager import session_scope


class RagStatsGateway(RagStatsPort):
    def read(self) -> RagStatsDto:
        with session_scope() as session:
            by_source = [
                RagSourceStatsDto(*row)
                for row in session.execute(
                    text(
                        """
                        select source_type, count(*), count(embedding), max(published_at)
                        from rag_chunk group by source_type order by count(*) desc
                        """
                    )
                )
            ]
            embedded_by = [
                EmbedderCountDto(*row)
                for row in session.execute(
                    text(
                        """
                        select embedded_by, count(*) from rag_chunk
                        where embedded_by is not null group by embedded_by order by count(*) desc
                        """
                    )
                )
            ]
        return RagStatsDto(
            total_chunks=sum(s.chunks for s in by_source),
            embedded_chunks=sum(s.embedded for s in by_source),
            by_source=by_source,
            embedded_by=embedded_by,
        )
