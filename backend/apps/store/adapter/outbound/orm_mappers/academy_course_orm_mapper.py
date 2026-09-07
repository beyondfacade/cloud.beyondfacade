"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.store.adapter.outbound.orms.academy_course_orm import AcademyCourseOrm
from apps.store.domain.entities.academy_course_entity import AcademyCourse


def to_orm(entity: AcademyCourse) -> AcademyCourseOrm:
    return AcademyCourseOrm(
        course_id=entity.course_id,
        store_id=entity.store_id,
        course_name=entity.course_name,
        tuition_fee=entity.tuition_fee,
        target_grade=entity.target_grade,
    )


def to_entity(orm: AcademyCourseOrm) -> AcademyCourse:
    return AcademyCourse(
        course_id=orm.course_id,
        store_id=orm.store_id,
        course_name=orm.course_name,
        tuition_fee=orm.tuition_fee,
        target_grade=orm.target_grade,
    )
