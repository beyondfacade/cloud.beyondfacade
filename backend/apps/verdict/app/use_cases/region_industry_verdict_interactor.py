"""Application Service — 얇은 조율: 게이트웨이 3종 → 업종별 분포 → 신호 평가 → 판정 → 업서트 → 제외 업종 prune."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    AlternativeIndustryDto,
    AlternativeRegionDto,
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    RegionIndustryVerdictDto,
    SignalResultDto,
    StoreSignalStat,
    VerdictAlternativesDto,
    VerdictValueDto,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import (
    RegionIndustryVerdictUseCase,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    IndustryCatalogPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_STRONG,
    VERDICT_ORANGE,
    RegionIndustryVerdict,
    SignalResult,
)
from apps.verdict.domain.errors import IndustryNotFoundError
from apps.verdict.domain.services.alternatives import rank_alternatives
from apps.verdict.domain.services.rules import judge, on_count, strong_count
from apps.verdict.domain.services.signals import SIGNALS, Signal, SignalInput
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS, VerdictThresholds

_EMPTY_STAT = dict(
    start_store_count=0, opened_12m=0, closed_12m=0, cohort_size=0, cohort_survived=0,
    closed_3y_count=0, closed_3y_median_months=None,
)


class RegionIndustryVerdictInteractor(RegionIndustryVerdictUseCase):
    def __init__(
        self,
        repository: RegionIndustryVerdictRepositoryPort,
        store_stats: StoreSignalStatsPort,
        region_context: RegionContextPort,
        industry_catalog: IndustryCatalogPort,
        region_catalog: RegionCatalogPort,
        thresholds: VerdictThresholds = DEFAULT_THRESHOLDS,
        signals: Sequence[Signal] = SIGNALS,
    ) -> None:
        self._repository = repository
        self._store_stats = store_stats
        self._region_context = region_context
        self._industry_catalog = industry_catalog
        self._region_catalog = region_catalog
        self._thresholds = thresholds
        self._signals = tuple(signals)

    def myself(self) -> RegionIndustryVerdictDto:
        signals = tuple(
            SignalResultDto(key=s.key, level=LEVEL_STRONG if i == 0 else LEVEL_OFF, value=0.13 if i == 0 else 0.0,
                            percentile=95.0 if i == 0 else 10.0, evidence="배선 검증", source=s.source)
            for i, s in enumerate(self._signals)
        )
        return RegionIndustryVerdictDto(
            region_code="myself", industry_id="korean_food", verdict_code=VERDICT_ORANGE,
            strong_count=1, on_count=1, signals=signals, computed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
        )

    def build(self, today: date) -> int:
        industries = self._industry_catalog.judged_industries()
        stats = {(s.region_code, s.industry_id): s for s in self._store_stats.signal_stats(today)}
        counts = {(c.region_code, c.industry_id): c.store_count for c in self._region_context.latest_store_counts()}
        contexts = self._region_context.latest_contexts()
        computed_at = datetime.now(timezone.utc)
        verdicts: list[RegionIndustryVerdict] = []
        for industry in industries:
            inputs = [self._input(ctx, industry, stats, counts) for ctx in contexts]
            verdicts.extend(self._judge_industry(inputs, computed_at))
        processed = self._repository.upsert(verdicts)
        self._repository.delete_other_industries(i.industry_id for i in industries)  # 제외된 업종의 옛 행 prune
        return processed

    def list_verdict_values(self, industry_id: str) -> list[VerdictValueDto]:
        self._require_judged(industry_id)
        return [VerdictValueDto(v.region_code, v.verdict_code) for v in self._repository.list_by_industry(industry_id)]

    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdictDto | None:
        self._require_judged(industry_id)
        entity = self._repository.find(region_code, industry_id)
        return None if entity is None else _to_dto(entity)

    def alternatives(self, region_code: str, industry_id: str) -> VerdictAlternativesDto | None:
        industries = self._industry_catalog.judged_industries()
        if industry_id not in {i.industry_id for i in industries}:
            raise IndustryNotFoundError(industry_id)
        base = self._repository.find(region_code, industry_id)
        if base is None:
            return None
        names = {i.industry_id: i.name for i in industries}
        regions = {r.region_code: r for r in self._region_catalog.regions()}
        me = regions.get(region_code)
        neighborhood_type = me.neighborhood_type if me else None

        same_region = [v for v in self._repository.list_by_region(region_code) if v.industry_id != industry_id]
        same_type = [
            v for v in self._repository.list_by_industry(industry_id)
            if v.region_code != region_code and neighborhood_type is not None
            and (r := regions.get(v.region_code)) is not None and r.neighborhood_type == neighborhood_type
        ]
        return VerdictAlternativesDto(
            region_code=region_code, industry_id=industry_id, neighborhood_type=neighborhood_type,
            industries=tuple(
                AlternativeIndustryDto(v.industry_id, names[v.industry_id], v.verdict_code, v.strong_count, v.on_count)
                for v in rank_alternatives(base, same_region, key=lambda v: v.industry_id)
            ),
            regions=tuple(
                AlternativeRegionDto(v.region_code, regions[v.region_code].name, v.verdict_code, v.strong_count, v.on_count)
                for v in rank_alternatives(base, same_type, key=lambda v: v.region_code)
            ),
        )

    # --- 내부 ---

    def _require_judged(self, industry_id: str) -> None:
        if industry_id not in {i.industry_id for i in self._industry_catalog.judged_industries()}:
            raise IndustryNotFoundError(industry_id)

    @staticmethod
    def _input(ctx: RegionContext, industry: JudgedIndustry, stats, counts) -> SignalInput:
        stat = stats.get((ctx.region_code, industry.industry_id))
        stat_fields = {k: getattr(stat, k) for k in _EMPTY_STAT} if stat else dict(_EMPTY_STAT)
        return SignalInput(
            region_code=ctx.region_code, industry_id=industry.industry_id, industry_name=industry.name,
            latest_store_count=counts.get((ctx.region_code, industry.industry_id)),
            resident_total=ctx.resident_total, change_code=ctx.change_code, change_name=ctx.change_name,
            change_quarter=ctx.change_quarter, closed_months=ctx.closed_months,
            seoul_closed_months=ctx.seoul_closed_months, **stat_fields,
        )

    def _judge_industry(self, inputs: list[SignalInput], computed_at: datetime) -> list[RegionIndustryVerdict]:
        t = self._thresholds
        results: dict[str, list[SignalResult]] = {i.region_code: [] for i in inputs}
        for signal in self._signals:
            # 업종 안에서 가드를 통과한 동만 분포에 넣는다 (설계서 §3-2)
            distribution = [signal.worse(v) for i in inputs if (v := signal.raw_value(i, t)) is not None]
            for i in inputs:
                results[i.region_code].append(signal.evaluate(i, t, distribution))
        verdicts = []
        for i in inputs:
            r = tuple(results[i.region_code])
            verdicts.append(RegionIndustryVerdict(
                region_code=i.region_code, industry_id=i.industry_id, verdict_code=judge(r, t),
                strong_count=strong_count(r), on_count=on_count(r), signals=r, computed_at=computed_at,
            ))
        return verdicts


def _to_dto(entity: RegionIndustryVerdict) -> RegionIndustryVerdictDto:
    return RegionIndustryVerdictDto(
        region_code=entity.region_code, industry_id=entity.industry_id, verdict_code=entity.verdict_code,
        strong_count=entity.strong_count, on_count=entity.on_count,
        signals=tuple(SignalResultDto(**asdict(s)) for s in entity.signals), computed_at=entity.computed_at,
    )
