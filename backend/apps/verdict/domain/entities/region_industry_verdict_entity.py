"""verdict BC 엔티티 — 동×업종 판정 1행 (설계서 §4-2). 순수 파이썬, 프레임워크 import 없음."""

from dataclasses import dataclass
from datetime import datetime

# 신호 순서 = signals_json 순서 = 카드 표시 순서 (설계서 §3-1)
SIGNAL_KEYS: tuple[str, ...] = ("net_outflow", "survival_cliff", "early_closure", "saturation")

# 업종 특화 신호 — 특정 원천 프로필에만 있다 (업종 특화 신호 설계서 §9-2). 백테스트 정렬·표 칸은 ALL_SIGNAL_KEYS 순서.
# signals 튜플은 "항상 5개"가 아니라 프로필이 정한 개수·순서다: 인허가 5 · 편의점 6 · 부동산 6.
SPECIFIC_SIGNAL_KEYS: tuple[str, ...] = ("closure_rate", "tobacco_gap", "trade_per_office")
ALL_SIGNAL_KEYS: tuple[str, ...] = SIGNAL_KEYS + SPECIFIC_SIGNAL_KEYS

# 참고 신호 — 평가·저장은 하되 strong_count/on_count/evaluable_count(등급 계산)에서는 뺀다.
# (상권 축소는 여러 시점 백테스트 0.91~0.96×로 정보가 없어 신호에서 뺐다 — docs/verdict-backtest-multi.md ②.) 담배권 빈자리는 폐업 위험이 아니라 진입 가능성을 잰다(업종 특화 신호 설계서 §6-2).
# 사무소당 거래는 법정동→행정동 배분이 근사라 참고 신호다(업종 특화 신호 설계서 §11).
ADVISORY_SIGNAL_KEYS: frozenset[str] = frozenset({"tobacco_gap", "trade_per_office"})

LEVEL_OFF = "off"
LEVEL_ON = "on"
LEVEL_STRONG = "strong"
LEVEL_UNAVAILABLE = "unavailable"

VERDICT_RED = "red"
VERDICT_ORANGE = "orange"
VERDICT_CLEAR = "clear"
VERDICT_INSUFFICIENT = "insufficient"

# 판정 원천 — 판정 한 행이 어떤 원천에서 나왔나 (업종 특화 신호 설계서 §9). 카드 배지·백테스트 합산 범위가 이 값을 본다.
BASIS_PERMIT = "permit"  # 인허가 개별 점포 이력 (store)
BASIS_PROXY = "proxy"  # 대리 원천의 개별 이력 (편의점 = 담배소매인)
BASIS_AGGREGATE = "aggregate"  # 동×분기 집계 (부동산 = 서울시 상권분석)

# 판정 대상에서 빼는 업종 — 학원·어린이집(HANDOFF §0-11 보조축), 기타(비노출), 치킨(2017-09 이후 신규 인허가 없음),
# 편의점(스냅샷 전용 원천 — store 인허가 행이 없어 신호 3개가 영구 불가; 4단계 담배권 특화 신호로 재포함 심사)
#   (9/29 재포함 게이트 미달 — 경고 lift 1.00×, docs/verdict-backtest.md 재포함 심사 절),
# 부동산(원천에 폐업 이력 없음 — 브이월드 API·공공데이터 파일·서울 열린데이터 모두 현재 사무소만, 설계서 §7)
#   (9/29 재포함 게이트 미달 — 경고 lift 1.04×, docs/verdict-backtest.md 재포함 심사 절).
# 판정 대상 = 프론트 `INDUSTRIES`(14) − 편의점 − 부동산 = 12업종. 프론트는 `shared/verdict.ts`의 `VERDICT_EXCLUDED_INDUSTRIES`로
# 같은 차집합을 만든다 — `INDUSTRIES` 14종과 그대로 같은 집합이 아니다.
EXCLUDED_INDUSTRIES: frozenset[str] = frozenset(
    {"academy", "childcare", "restaurant_other", "chicken", "convenience_store", "real_estate"}
)

# 판정 근거가 약한 업종 — 여러 시점 백테스트(T=2019·2021·2022·2023)에서 lift ≥ 1.10×가 3번 이상인 신호가 하나도 없다
# (docs/verdict-backtest-multi.md ⑤, 2026-10-06 사용자 결정). 판정은 내되 비추천은 내지 않고(최대 조건부) "판정 근거 약함"을 밝힌다.
WEAK_BASIS_INDUSTRIES: frozenset[str] = frozenset(
    {"japanese_food", "pub", "snack", "gym", "pc_bang", "billiard", "karaoke"}
)


@dataclass(frozen=True)
class SignalResult:
    key: str  # SIGNAL_KEYS 중 하나
    level: str  # off | on | strong | unavailable
    value: float | None  # 원값. unavailable이면 None
    percentile: float | None  # 나쁜 방향 백분위 0~100. 이진 신호·unavailable은 None
    evidence: str  # 근거 한 문장 (설계서 §3-4)
    source: str  # store | metric | neighborhood
    band: str | None = None  # very_bad | bad | normal | good | very_good. 이진·unavailable·옛 행은 None
    band_label: str | None = None  # 예: "밀집 매우 높은 편"


@dataclass(frozen=True)
class RegionIndustryVerdict:
    region_code: str
    industry_id: str
    verdict_code: str  # red | orange | clear | insufficient
    strong_count: int
    on_count: int  # on + strong
    signals: tuple[SignalResult, ...]  # 프로필의 신호, 프로필 순서
    computed_at: datetime
    basis: str = BASIS_PERMIT  # permit | proxy | aggregate

    @property
    def weak_basis(self) -> bool:
        return self.industry_id in WEAK_BASIS_INDUSTRIES
