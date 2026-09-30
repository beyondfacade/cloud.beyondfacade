from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.services.scanner_paths import is_scanner_probe


def response_event_kind(status_code: int, path: str) -> AccessEventKind | None:
    """응답 1건이 보안 이벤트로 남을 가치가 있는지 — 5xx와 실패한 스캐너 경로 요청만."""
    if status_code >= 500:
        return AccessEventKind.SERVER_ERROR
    if status_code >= 400 and is_scanner_probe(path):
        return AccessEventKind.SCANNER_PROBE
    return None
