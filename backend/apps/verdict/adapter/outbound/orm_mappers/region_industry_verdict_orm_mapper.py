"""Outbound Boundary Gate — entity ↔ ORM 변환 (signals 튜플 ↔ JSON 문자열)."""

import json
from dataclasses import asdict

from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    RegionIndustryVerdict,
    SignalResult,
)


def to_orm(entity: RegionIndustryVerdict) -> RegionIndustryVerdictOrm:
    return RegionIndustryVerdictOrm(
        region_code=entity.region_code,
        industry_id=entity.industry_id,
        verdict_code=entity.verdict_code,
        strong_count=entity.strong_count,
        on_count=entity.on_count,
        signals_json=json.dumps([asdict(s) for s in entity.signals], ensure_ascii=False),
        computed_at=entity.computed_at,
    )


def to_entity(orm: RegionIndustryVerdictOrm) -> RegionIndustryVerdict:
    return RegionIndustryVerdict(
        region_code=orm.region_code,
        industry_id=orm.industry_id,
        verdict_code=orm.verdict_code,
        strong_count=orm.strong_count,
        on_count=orm.on_count,
        signals=tuple(SignalResult(**item) for item in json.loads(orm.signals_json)),
        computed_at=orm.computed_at,
    )
