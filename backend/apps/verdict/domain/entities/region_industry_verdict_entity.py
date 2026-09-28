"""verdict BC 엔티티 — 동×업종 판정 1행 (설계서 §4-2). 순수 파이썬, 프레임워크 import 없음."""

from dataclasses import dataclass
from datetime import datetime

# 신호 순서 = signals_json 순서 = 카드 표시 순서 (설계서 §3-1)
SIGNAL_KEYS: tuple[str, ...] = ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")

LEVEL_OFF = "off"
LEVEL_ON = "on"
LEVEL_STRONG = "strong"
LEVEL_UNAVAILABLE = "unavailable"

VERDICT_RED = "red"
VERDICT_ORANGE = "orange"
VERDICT_CLEAR = "clear"
VERDICT_INSUFFICIENT = "insufficient"

# 판정 대상에서 빼는 업종 — 학원·어린이집(HANDOFF §0-11 보조축), 기타(비노출), 치킨(2017-09 이후 신규 인허가 없음).
# 프론트 `shared/industries.ts`의 INDUSTRIES 14종과 같은 집합이어야 한다.
EXCLUDED_INDUSTRIES: frozenset[str] = frozenset({"academy", "childcare", "restaurant_other", "chicken"})


@dataclass(frozen=True)
class SignalResult:
    key: str  # SIGNAL_KEYS 중 하나
    level: str  # off | on | strong | unavailable
    value: float | None  # 원값. unavailable이면 None
    percentile: float | None  # 나쁜 방향 백분위 0~100. 이진 신호·unavailable은 None
    evidence: str  # 근거 한 문장 (설계서 §3-4)
    source: str  # store | metric | neighborhood


@dataclass(frozen=True)
class RegionIndustryVerdict:
    region_code: str
    industry_id: str
    verdict_code: str  # red | orange | clear | insufficient
    strong_count: int
    on_count: int  # on + strong
    signals: tuple[SignalResult, ...]  # 항상 5개, SIGNAL_KEYS 순서
    computed_at: datetime
