from abc import ABC, abstractmethod

from apps.admin.domain.entities.security_setting_entity import SecuritySetting


class SecuritySettingRepositoryPort(ABC):
    @abstractmethod
    def get(self, key: str) -> SecuritySetting:
        """저장된 행이 없으면 기본값."""

    @abstractmethod
    def save(self, setting: SecuritySetting) -> SecuritySetting: ...
