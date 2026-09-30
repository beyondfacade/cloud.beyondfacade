from dataclasses import dataclass
from datetime import datetime

AUTO_DEFENSE = "auto_defense"

# 행이 없을 때의 값 — 배포 직후에도 방어가 켜진 채로 시작한다
_DEFAULTS = {AUTO_DEFENSE: True}


@dataclass
class SecuritySetting:
    """보안 동작 스위치 — key마다 한 행."""

    key: str
    enabled: bool
    updated_at: datetime | None = None
    updated_by: int | None = None

    @classmethod
    def default(cls, key: str) -> "SecuritySetting":
        return cls(key=key, enabled=_DEFAULTS[key])
