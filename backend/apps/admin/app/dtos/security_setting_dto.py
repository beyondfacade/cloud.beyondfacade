from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class AutoBlockRuleDto:
    rule: str
    title: str
    threshold: int
    window_minutes: int
    block_minutes: int
    repeat_block_minutes: int


@dataclass(frozen=True)
class AutoDefenseDto:
    enabled: bool
    updated_at: datetime | None
    updated_by: str | None  # 마지막으로 켜고 끈 관리자 username
    rules: list[AutoBlockRuleDto] = field(default_factory=list)
