from dataclasses import dataclass


@dataclass
class CommerceIngestResultDto:
    """적재 1회 결과 — CLI가 그대로 보고한다. 미해석 행정동은 버리지 않고 건수로만 드러낸다."""

    processed: int  # 업서트한 행 수
    region_resolved: int  # region_code가 기입된 행 수
    region_unresolved: int  # 앞 8자리 미매칭으로 region_code가 NULL인 행 수
