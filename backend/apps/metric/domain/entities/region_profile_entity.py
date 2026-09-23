from dataclasses import dataclass


@dataclass(frozen=True)
class RegionProfile:
    """행정동×분기 동네 프로필 — 원자료 999만 행에서 사람이 읽을 수 있는 것만 뽑은 파생 계층.

    지표 6개를 판정과 함께 저장하는 이유는 화면에서 근거를 보여주기 위해서다. 판정만 저장하면
    "왜 그렇게 나왔는지"를 다시 계산해야 한다. 저장하는 값은 **판정에 실제로 쓰인 4분기 평활
    값**이며, 근거 문장(`type_reason`)의 수치와 일치한다 (설계서 §4-1 · §5-2).
    """

    region_code: str
    year_quarter: str
    neighborhood_type: str  # office | campus | dining | hub | residential | mixed
    type_reason: str
    time_label: str | None  # morning | day | evening | night | flat
    peak_block: str | None  # morning | day | evening | night
    trough_block: str | None
    worker_resident_ratio: float | None  # 직장인구 결측 11개 동은 None (0으로 채우면 주거형 오판)
    weekend_index: float | None
    night_index: float | None
    footfall_20s_share: float | None
    fnb_share: float | None
    facility_total: int | None
    resident_total: int | None
    # 4블록 시간당 강도(아침·낮·저녁·밤). 배치가 4분기 평활한 시간대에서 계산한다 — 화면이 원값으로
    # 보정을 다시 하면 두 곳 중 하나가 언젠가 틀린다 (무대 설계서 §5-1)
    block_morning: float | None = None
    block_day: float | None = None
    block_evening: float | None = None
    block_night: float | None = None
