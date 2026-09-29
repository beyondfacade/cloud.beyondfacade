"""Application Service — 얇은 조율: 업종별 원천(기본 인허가 포트 3종) → 업종별 분포 → 신호 평가 → 판정 → 업서트 → 제외 업종 prune."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    AlternativeIndustryDto,
    AlternativeRegionDto,
    BacktestBucketDto,
    BacktestGateDto,
    BacktestReportDto,
    BacktestSignalBucketDto,
    EntrantOutcome,
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
    EntrantOutcomePort,
    IndustryCatalogPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.industry_source import IndustrySource, PermitSignalData
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_STRONG,
    VERDICT_ORANGE,
    RegionIndustryVerdict,
    SignalResult,
)
from apps.verdict.domain.errors import IndustryNotFoundError
from apps.verdict.domain.services.alternatives import rank_alternatives
from apps.verdict.domain.services.backtest import GATE_POLICIES, quarter_before, reinclusion_gate, summarize, summarize_signals
from apps.verdict.domain.services.profiles import PermitProfile, SignalProfile
from apps.verdict.domain.services.rules import judge, on_count, strong_count
from apps.verdict.domain.services.signals import SIGNALS, Signal, SignalInput
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS, VerdictThresholds

_EMPTY_STAT = dict(
    start_store_count=0, opened_12m=0, closed_12m=0, cohort_size=0, cohort_survived=0,
    closed_3y_count=0, closed_3y_median_months=None, gap_candidates=0, gap_blocked=0, trade_12m=None,
)


class RegionIndustryVerdictInteractor(RegionIndustryVerdictUseCase):
    def __init__(
        self,
        repository: RegionIndustryVerdictRepositoryPort,
        store_stats: StoreSignalStatsPort,
        region_context: RegionContextPort,
        industry_catalog: IndustryCatalogPort,
        region_catalog: RegionCatalogPort,
        entrant_outcomes: EntrantOutcomePort,
        thresholds: VerdictThresholds = DEFAULT_THRESHOLDS,
        signals: Sequence[Signal] = SIGNALS,
        sources: Mapping[str, IndustrySource] | None = None,
    ) -> None:
        self._repository = repository
        self._region_context = region_context
        self._industry_catalog = industry_catalog
        self._region_catalog = region_catalog
        self._thresholds = thresholds
        self._signals = tuple(signals)
        # 등록 안 된 업종의 원천 = 기존 인허가 포트 3개 (업종 특화 신호 설계서 §4). 업종별 교체는 sources로만.
        self._default_source = IndustrySource(
            PermitProfile(self._signals), PermitSignalData(store_stats, region_context, entrant_outcomes)
        )
        self._sources = dict(sources or {})

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
        verdicts = self.compute(today)
        processed = self._repository.upsert(verdicts)
        self._repository.delete_other_industries({v.industry_id for v in verdicts})  # 제외된 업종의 옛 행 prune
        return processed

    def compute(
        self, today: date, quarter_max: str | None = None, year_max: int | None = None,
        industries: Sequence[JudgedIndustry] | None = None,
    ) -> list[RegionIndustryVerdict]:
        """판정 대상(또는 주어진) 업종 × 전 행정동 판정 (저장 없음). 업종마다 등록된 원천·프로필을 쓴다(업종 특화 신호 설계서 §4).
        상한은 백테스트가 T 시점 이후 값을 못 보게 막는다 (판정 카드 설계서 §13)."""
        targets = self._industry_catalog.judged_industries() if industries is None else list(industries)
        contexts = self._region_context.latest_contexts(quarter_max)
        computed_at = datetime.now(timezone.utc)
        loaded: dict[IndustrySource, tuple[dict, dict]] = {}
        verdicts: list[RegionIndustryVerdict] = []
        for industry in targets:
            source = self._source_of(industry.industry_id)
            if source not in loaded:  # 원천마다 한 번만 읽는다 (인허가 원천은 store 전량 group_by 1회)
                loaded[source] = self._load(source, today, quarter_max, year_max)
            stats, counts = loaded[source]
            inputs = [self._input(ctx, industry, stats, counts) for ctx in contexts]
            verdicts.extend(self._judge_industry(inputs, computed_at, source.profile))
        return verdicts

    def backtest(
        self, as_of: date, entry_days: int = 365, horizon_days: int = 1095, industry_ids: Sequence[str] | None = None
    ) -> BacktestReportDto:
        quarter_max, year_max = quarter_before(as_of), as_of.year - 1
        industries = (
            self._industry_catalog.judged_industries() if industry_ids is None
            else self._industry_catalog.named_industries(industry_ids)
        )
        verdicts = self.compute(as_of, quarter_max=quarter_max, year_max=year_max, industries=industries)
        outcomes = self._outcomes(industries, as_of, entry_days, horizon_days)
        names = {i.industry_id: i.name for i in industries}
        basis_of = {i.industry_id: self._source_of(i.industry_id).profile.basis for i in industries}
        buckets = summarize(verdicts, outcomes)
        return BacktestReportDto(
            as_of=as_of, quarter_max=quarter_max, year_max=year_max, entry_days=entry_days, horizon_days=horizon_days,
            buckets=tuple(
                BacktestBucketDto(b.industry_id, names.get(b.industry_id), b.verdict_code, b.pairs, b.opened, b.closed)
                for b in buckets
            ),
            signal_buckets=tuple(
                BacktestSignalBucketDto(b.industry_id, names.get(b.industry_id), b.signal_key, b.fired, b.pairs, b.opened, b.closed)
                for b in summarize_signals(verdicts, outcomes)
            ),
            industry_basis=tuple(basis_of.items()),
            gates=tuple(
                BacktestGateDto(g.industry_id, names.get(g.industry_id), basis_of[g.industry_id], g.passed, g.warn_lift,
                                g.warn_opened, g.clear_opened, g.warn_pairs, g.clear_pairs, g.reason)
                for g in (reinclusion_gate(buckets, i, GATE_POLICIES[basis_of[i]]) for i in basis_of)
            ),
        )

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

    def _source_of(self, industry_id: str) -> IndustrySource:
        return self._sources.get(industry_id, self._default_source)

    @staticmethod
    def _load(source: IndustrySource, today: date, quarter_max: str | None, year_max: int | None) -> tuple[dict, dict]:
        stats = {(s.region_code, s.industry_id): s for s in source.data.signal_stats(today)}
        counts = {(c.region_code, c.industry_id): c.store_count for c in source.data.store_counts(year_max, quarter_max)}
        return stats, counts

    def _outcomes(
        self, industries: Sequence[JudgedIndustry], as_of: date, entry_days: int, horizon_days: int
    ) -> list[EntrantOutcome]:
        """원천마다 한 번 읽고 그 원천이 맡은 업종의 결과만 남긴다 (인허가 원천의 부동산 행 등은 버린다)."""
        members: dict[IndustrySource, set[str]] = {}
        for industry in industries:
            members.setdefault(self._source_of(industry.industry_id), set()).add(industry.industry_id)
        return [
            outcome
            for source, ids in members.items()
            for outcome in source.data.entrant_outcomes(as_of, entry_days, horizon_days)
            if outcome.industry_id in ids
        ]

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

    def _judge_industry(
        self, inputs: list[SignalInput], computed_at: datetime, profile: SignalProfile
    ) -> list[RegionIndustryVerdict]:
        t = self._thresholds
        results: dict[str, list[SignalResult]] = {i.region_code: [] for i in inputs}
        for signal in profile.signals():
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
                basis=profile.basis,
            ))
        return verdicts


def _to_dto(entity: RegionIndustryVerdict) -> RegionIndustryVerdictDto:
    return RegionIndustryVerdictDto(
        region_code=entity.region_code, industry_id=entity.industry_id, verdict_code=entity.verdict_code,
        strong_count=entity.strong_count, on_count=entity.on_count,
        signals=tuple(SignalResultDto(**asdict(s)) for s in entity.signals), computed_at=entity.computed_at,
        basis=entity.basis,
    )
