"""ops 조치를 admin BC 감사 로그로 넘긴다 (cross-BC 호출은 이 구현체 안에서만)."""

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.dependencies.admin_dependencies import get_admin_audit_use_case
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.ops.app.dtos.ops_history_dto import OpsActorDto
from apps.ops.app.ports.output.ops_audit_port import OpsAuditPort


class AdminAuditGateway(OpsAuditPort):
    def record(self, actor: OpsActorDto, action: str, target: str, detail: str = "") -> None:
        principal = AdminPrincipalDto(id=actor.id, username=actor.username, role="operator", can_operate=True)
        get_admin_audit_use_case().record(principal, AuditAction(action), target, detail, actor.ip)
