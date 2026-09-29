"""백테스트 집계 — T 시점 판정과 그 뒤 진입 코호트의 실제 폐업을 (동, 업종)으로 조인해 판정 코드별로 센다 (설계서 §13).
순수 파이썬. 폐업률·lift는 버킷이 스스로 계산한다."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    ALL_SIGNAL_KEYS,
    BASIS_AGGREGATE,
    BASIS_PERMIT,
    BASIS_PROXY,
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    RegionIndustryVerdict,
)

VERDICT_ORDER: tuple[str, ...] = ("red", "orange", "clear", "insufficient")


def _pooled(industry_id: str) -> tuple[str | None, ...]:
    return (None, industry_id)


def _own(industry_id: str) -> tuple[str | None, ...]:
    return (industry_id,)


# 버킷 범위 — 전체(None) 합산에 넣을지는 판정 원천이 정한다. 집계 기반은 결과 단위(점포수 대비 폐업)가 달라
# 진입 코호트와 합산하지 않는다 (업종 특화 신호 설계서 §7-3). 표 조회라 분기 없음.
_SCOPES_OF_BASIS = {BASIS_PERMIT: _pooled, BASIS_PROXY: _pooled, BASIS_AGGREGATE: _own}


def quarter_before(as_of: date) -> str:
    """as_of가 속한 분기의 직전 분기 라벨('20221') — T 시점에 확정돼 있던 마지막 분기."""
    quarter = (as_of.month - 1) // 3 + 1
    return f"{as_of.year - 1}4" if quarter == 1 else f"{as_of.year}{quarter - 1}"


def quarter_of(d: date) -> str:
    """d가 속한 분기 라벨('20222')."""
    return f"{d.year}{(d.month - 1) // 3 + 1}"


def shift_quarter(year_quarter: str, n: int) -> str:
    """분기 라벨을 n분기 옮긴다 — shift_quarter('20254', -4) == '20244'."""
    index = int(year_quarter[:4]) * 4 + int(year_quarter[4]) - 1 + n
    return f"{index // 4}{index % 4 + 1}"


@dataclass(frozen=True)
class OutcomeBucket:
    industry_id: str | None  # None = 전체
    verdict_code: str
    pairs: int  # 동×업종 조합 수 (개업 0인 조합 포함)
    opened: int
    closed: int

    @property
    def rate(self) -> float | None:
        return None if self.opened == 0 else self.closed / self.opened


def summarize(verdicts: Sequence[RegionIndustryVerdict], outcomes: Iterable[EntrantOutcome]) -> list[OutcomeBucket]:
    """전체 버킷(industry_id None) 다음에 업종별 버킷. 판정이 없는 결과 행은 버린다."""
    by_key = {(o.region_code, o.industry_id): o for o in outcomes}
    acc: dict[tuple[str | None, str], list[int]] = {}
    for v in verdicts:
        o = by_key.get((v.region_code, v.industry_id))
        opened, closed = (o.opened, o.closed_within) if o else (0, 0)
        for industry in _SCOPES_OF_BASIS[v.basis](v.industry_id):
            cell = acc.setdefault((industry, v.verdict_code), [0, 0, 0])
            cell[0] += 1
            cell[1] += opened
            cell[2] += closed
    ordered = sorted(acc, key=lambda k: (k[0] is not None, k[0] or "", VERDICT_ORDER.index(k[1])))
    return [OutcomeBucket(industry, code, *acc[(industry, code)]) for industry, code in ordered]


@dataclass(frozen=True)
class SignalBucket:
    """신호 하나의 켜짐(on·strong) vs 꺼짐(off) 버킷. unavailable은 어느 쪽에도 넣지 않는다."""

    industry_id: str | None  # None = 전체
    signal_key: str
    fired: bool
    pairs: int
    opened: int
    closed: int

    @property
    def rate(self) -> float | None:
        return None if self.opened == 0 else self.closed / self.opened


_FIRED_OF = {LEVEL_STRONG: True, LEVEL_ON: True, LEVEL_OFF: False}


def summarize_signals(verdicts: Sequence[RegionIndustryVerdict], outcomes: Iterable[EntrantOutcome]) -> list[SignalBucket]:
    """신호별로 '켜진 동×업종'과 '꺼진 동×업종'의 진입 코호트 폐업을 센다 — 어느 신호가 맞히는가 (설계서 §13)."""
    by_key = {(o.region_code, o.industry_id): o for o in outcomes}
    acc: dict[tuple[str | None, str, bool], list[int]] = {}
    for v in verdicts:
        o = by_key.get((v.region_code, v.industry_id))
        opened, closed = (o.opened, o.closed_within) if o else (0, 0)
        for signal in v.signals:
            fired = _FIRED_OF.get(signal.level)
            if fired is None:
                continue
            for industry in _SCOPES_OF_BASIS[v.basis](v.industry_id):
                cell = acc.setdefault((industry, signal.key, fired), [0, 0, 0])
                cell[0] += 1
                cell[1] += opened
                cell[2] += closed
    ordered = sorted(acc, key=lambda k: (k[0] is not None, k[0] or "", ALL_SIGNAL_KEYS.index(k[1]), not k[2]))
    return [SignalBucket(industry, key, fired, *acc[(industry, key, fired)]) for industry, key, fired in ordered]


@dataclass(frozen=True)
class GatePolicy:
    min_lift: float  # 경고(🔴+🟠) 폐업률 ÷ ⚪ 폐업률 하한
    min_opened: int  # 경고·⚪ 각각의 개업(또는 집계 노출) 하한
    min_pairs: int  # 경고·⚪ 각각의 동×업종 하한


# 재포함 게이트 (업종 특화 신호 설계서 §8). 1.10 = 작동한다고 본 카페 1.36·미용실 1.16과 못 가른 나머지(≤1.08) 사이.
# 대리 원천은 개업 50곳(폐업률 15%에서 표준오차 약 5%p), 집계 원천은 결과 단위가 동이라 동 30곳.
GATE_POLICIES: dict[str, GatePolicy] = {
    BASIS_PERMIT: GatePolicy(min_lift=1.10, min_opened=50, min_pairs=0),
    BASIS_PROXY: GatePolicy(min_lift=1.10, min_opened=50, min_pairs=0),
    BASIS_AGGREGATE: GatePolicy(min_lift=1.10, min_opened=0, min_pairs=30),
}

_WARN_CODES = frozenset({"red", "orange"})


@dataclass(frozen=True)
class GateResult:
    industry_id: str
    passed: bool
    warn_lift: float | None
    warn_opened: int
    clear_opened: int
    warn_pairs: int
    clear_pairs: int
    reason: str  # "통과" 또는 "미달 — …"


def _fmt_lift(lift: float | None) -> str:
    return "계산 불가" if lift is None else f"{lift:.2f}×"


def reinclusion_gate(buckets: Iterable[OutcomeBucket], industry_id: str, policy: GatePolicy) -> GateResult:
    """업종 버킷으로 재포함 게이트를 판정한다. 보류(insufficient)는 넣지 않는다."""
    own = [b for b in buckets if b.industry_id == industry_id]
    warn = [b for b in own if b.verdict_code in _WARN_CODES]
    clear = [b for b in own if b.verdict_code == "clear"]
    w_pairs, w_opened, w_closed = sum(b.pairs for b in warn), sum(b.opened for b in warn), sum(b.closed for b in warn)
    c_pairs, c_opened, c_closed = sum(b.pairs for b in clear), sum(b.opened for b in clear), sum(b.closed for b in clear)
    lift = None if not (w_opened and c_opened and c_closed) else (w_closed / w_opened) / (c_closed / c_opened)
    failures = [
        message
        for failed, message in (
            (min(w_pairs, c_pairs) < policy.min_pairs,
             f"동×업종 경고 {w_pairs}·경고 없음 {c_pairs} < {policy.min_pairs}"),
            (min(w_opened, c_opened) < policy.min_opened,
             f"개업 경고 {w_opened:,}·경고 없음 {c_opened:,} < {policy.min_opened}"),
            (lift is None or lift < policy.min_lift,
             f"경고 lift {_fmt_lift(lift)} < {policy.min_lift:.2f}×"),
        )
        if failed
    ]
    reason = "통과" if not failures else "미달 — " + "; ".join(failures)
    return GateResult(industry_id, not failures, lift, w_opened, c_opened, w_pairs, c_pairs, reason)
