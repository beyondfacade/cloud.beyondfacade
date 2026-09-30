from abc import ABC, abstractmethod

from apps.ops.app.dtos.ops_history_dto import OpsActorDto


class OpsAuditPort(ABC):
    @abstractmethod
    def record(self, actor: OpsActorDto, action: str, target: str, detail: str = "") -> None:
        """action은 관리자 감사 로그 조치 이름(probe.run·collector.run)."""
