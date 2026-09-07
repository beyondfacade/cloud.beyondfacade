"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.funding.domain.entities.funding_program_entity import FundingProgram

_FIELDS = (
    "program_id",
    "source",
    "title",
    "org",
    "url",
    "apply_period",
    "exec_org",
    "field_category",
    "field_subcategory",
    "target_text",
    "hashtags",
    "apply_begin",
    "deadline",
    "summary",
    "posted_at",
    "source_updated_at",
    "is_expired",
)


def to_orm(entity: FundingProgram) -> FundingProgramOrm:
    return FundingProgramOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: FundingProgramOrm) -> FundingProgram:
    return FundingProgram(**{name: getattr(orm, name) for name in _FIELDS})


def apply_to_orm(entity: FundingProgram, orm: FundingProgramOrm) -> None:
    """업서트 갱신 — is_expired는 만료 배치가 관리하므로 덮어쓰지 않는다."""
    for name in _FIELDS:
        if name == "is_expired":
            continue
        setattr(orm, name, getattr(entity, name))
