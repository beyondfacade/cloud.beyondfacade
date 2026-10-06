"""신호 프로필 — 업종의 원천에 따라 어떤 신호를 어떤 원천 표기로 돌리는가 (Strategy, 업종 특화 신호 설계서 §4).
인터랙터는 업종 id로 프로필을 찾기만 하고 업종을 분기하지 않는다."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    BASIS_AGGREGATE,
    BASIS_PERMIT,
    BASIS_PROXY,
)
from apps.verdict.domain.services.signals import (
    SIGNALS,
    ClosureRateSignal,
    EarlyClosureSignal,
    NetOutflowSignal,
    SaturationSignal,
    Signal,
    SourcedSignal,
    SurvivalCliffSignal,
    TobaccoGapSignal,
    TradePerOfficeSignal,
    UnsupportedSignal,
)

_TOBACCO = "tobacco"
_COMMERCE = "commerce"
_NO_STORE_HISTORY = "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"


class SignalProfile(ABC):
    basis: str

    @abstractmethod
    def signals(self) -> tuple[Signal, ...]:
        """표시·저장 순서대로의 신호 목록."""


class PermitProfile(SignalProfile):
    """인허가 개별 이력 — 공통 신호 5개 그대로 (판정 카드 설계서 §3)."""

    basis = BASIS_PERMIT

    def __init__(self, signals: Sequence[Signal] = SIGNALS) -> None:
        self._signals = tuple(signals)

    def signals(self) -> tuple[Signal, ...]:
        return self._signals


class TobaccoProxyProfile(SignalProfile):
    """편의점 — 담배소매인 이력으로 공통 신호를 돌리고 담배권 빈자리(참고)를 더한다 (설계서 §5·§6)."""

    basis = BASIS_PROXY

    def signals(self) -> tuple[Signal, ...]:
        return (
            SourcedSignal(NetOutflowSignal(), _TOBACCO),
            SourcedSignal(SurvivalCliffSignal(), _TOBACCO),
            SourcedSignal(EarlyClosureSignal(), _TOBACCO),
            SourcedSignal(SaturationSignal(), _TOBACCO),
            TobaccoGapSignal(),
        )


class AggregateProfile(SignalProfile):
    """부동산 — 동×분기 집계로 폐업률·포화만. 코호트 신호는 원천상 불가 (설계서 §7)."""

    basis = BASIS_AGGREGATE

    def signals(self) -> tuple[Signal, ...]:
        return (
            ClosureRateSignal(),
            UnsupportedSignal(SurvivalCliffSignal.key, _COMMERCE, _NO_STORE_HISTORY),
            UnsupportedSignal(EarlyClosureSignal.key, _COMMERCE, _NO_STORE_HISTORY),
            SourcedSignal(SaturationSignal(), _COMMERCE),
            TradePerOfficeSignal(),
        )
