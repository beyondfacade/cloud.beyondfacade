"""관리자 기록 보존 정리 — 매일 크론(scripts/admin-housekeeping.sh)이 부른다.

    python -m apps.admin.adapter.inbound.cli.admin_housekeeping
"""

from apps.admin.dependencies.admin_dependencies import get_housekeeping_use_case


def main() -> None:
    result = get_housekeeping_use_case().run()
    print(
        f"정리 완료 — 보안 이벤트 {result.access_events}건 · 감사 로그 {result.audit_entries}건 · "
        f"만료 세션 {result.sessions}건 · 만료 차단 {result.ip_blocks}건"
    )


if __name__ == "__main__":
    main()
