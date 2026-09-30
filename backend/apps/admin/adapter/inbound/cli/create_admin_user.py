"""계정 생성·비밀번호 재설정 — 화면에서는 남의 계정을 만들거나 비밀번호를 바꿀 수 없어 이 CLI로만 한다.

    python -m apps.admin.adapter.inbound.cli.create_admin_user --username ops --role operator

비밀번호는 프롬프트로 두 번 받는다. 비대화형 실행은 ADMIN_PASSWORD 환경변수로 넘긴다
(셸 히스토리에 남지 않게 인자로는 받지 않는다).
"""

import argparse
import getpass
import os
import sys

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.admin_user_entity import AdminRole


def _read_password() -> str:
    from_env = os.environ.get("ADMIN_PASSWORD")
    if from_env:
        return from_env
    first = getpass.getpass("비밀번호: ")
    if first != getpass.getpass("비밀번호 확인: "):
        sys.exit("비밀번호가 서로 다릅니다.")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="관리자 계정 생성·재설정")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=[role.value for role in AdminRole], default=AdminRole.VIEWER.value)
    args = parser.parse_args()
    try:
        principal = get_admin_user_use_case().upsert(args.username, _read_password(), args.role)
    except ValueError as error:
        sys.exit(str(error))
    print(f"관리자 계정 준비됨: {principal.username} ({principal.role})")


if __name__ == "__main__":
    main()
