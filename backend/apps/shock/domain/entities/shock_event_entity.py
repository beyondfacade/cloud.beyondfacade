from dataclasses import dataclass, field
from datetime import date

from apps.shock.domain.value_objects.shock_layer import Severity, ShockLayer


@dataclass(frozen=True)
class IndustryImpact:
    """업종 영향 VO — shock_event_industry 1행 (industry는 ID로만 참조)."""

    industry_id: str
    severity: str  # Severity 값

    def __post_init__(self) -> None:
        if self.severity not in Severity:
            raise ValueError(f"허용되지 않는 severity: {self.severity}")


@dataclass
class ShockEvent:
    """특이변수(외생 충격) Aggregate Root — 업종 영향(industry_impacts)까지 불변식을 지킨다.

    지원금류 충격은 폐업 '지연' 왜곡(brainstorming §5.2 ⚠️)을 description에 담아
    후속 분석이 참조할 수 있게 한다. 출처(source)는 모든 행 필수.
    """

    event_id: str
    layer: str  # ShockLayer 값
    name: str
    start_date: date
    scope: str  # 전국 / 서울 / 수도권 등
    source: str  # 근거 출처 (기관·고시·API명) — 필수
    end_date: date | None = None  # 진행 중·상시 효과는 None
    source_url: str | None = None
    description: str | None = None
    industry_impacts: list[IndustryImpact] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.layer not in ShockLayer:
            raise ValueError(f"허용되지 않는 layer: {self.layer}")
        if not self.source:
            raise ValueError("근거 출처(source) 없는 충격은 등록할 수 없다")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError(f"종료일이 시행일보다 빠르다: {self.event_id}")
