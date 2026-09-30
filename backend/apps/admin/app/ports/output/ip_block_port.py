from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.ip_block_entity import IpBlock


class IpBlockRepositoryPort(ABC):
    @abstractmethod
    def list_active(self, now: datetime) -> list[IpBlock]: ...

    @abstractmethod
    def get(self, ip: str) -> IpBlock | None: ...

    @abstractmethod
    def save(self, block: IpBlock) -> None:
        """ip 기준 생성 또는 사유·만료 갱신."""

    @abstractmethod
    def delete(self, ip: str) -> bool:
        """삭제했으면 True, 없던 IP면 False."""
