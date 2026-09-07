from sqlalchemy import delete

from apps.store.adapter.outbound.orm_mappers.academy_course_orm_mapper import to_orm
from apps.store.adapter.outbound.orms.academy_course_orm import AcademyCourseOrm
from apps.store.app.ports.output.academy_course_port import AcademyCourseRepositoryPort
from apps.store.domain.entities.academy_course_entity import AcademyCourse
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAcademyCourseRepository(AcademyCourseRepositoryPort):
    def replace_for_stores(self, courses_by_store: dict[str, list[AcademyCourse]]) -> int:
        if not courses_by_store:
            return 0
        rows = [to_orm(c) for courses in courses_by_store.values() for c in courses]
        with session_scope() as session:
            session.execute(
                delete(AcademyCourseOrm).where(
                    AcademyCourseOrm.store_id.in_(courses_by_store.keys())
                )
            )
            session.add_all(rows)
        return len(rows)
