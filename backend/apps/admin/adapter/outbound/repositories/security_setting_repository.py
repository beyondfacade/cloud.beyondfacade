from apps.admin.adapter.outbound.orm_mappers.security_setting_orm_mapper import apply_to_orm, to_entity, to_orm
from apps.admin.adapter.outbound.orms.security_setting_orm import SecuritySettingOrm
from apps.admin.app.ports.output.security_setting_port import SecuritySettingRepositoryPort
from apps.admin.domain.entities.security_setting_entity import SecuritySetting
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemySecuritySettingRepository(SecuritySettingRepositoryPort):
    def get(self, key: str) -> SecuritySetting:
        with session_scope() as session:
            orm = session.get(SecuritySettingOrm, key)
            return to_entity(orm) if orm else SecuritySetting.default(key)

    def save(self, setting: SecuritySetting) -> SecuritySetting:
        with session_scope() as session:
            orm = session.get(SecuritySettingOrm, setting.key)
            if orm is None:
                session.add(to_orm(setting))
            else:
                apply_to_orm(setting, orm)
        return setting
