"""회원 등급 지정 — 가입(비밀번호·구글)은 모두 일반이라 첫 관리자는 이 CLI로 올린다.

    python -m apps.admin.adapter.inbound.cli.set_admin_role --username kim --role operator

operator = 관리자(쓰기), viewer = 일반(읽기). 이후 등급 변경은 인사팀 화면에서 관리자가 한다.
"""

import argparse
import sys

from apps.admin.app.errors import AdminError
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.admin_user_entity import AdminRole


def main() -> None:
    parser = argparse.ArgumentParser(description="회원 등급 지정")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=[role.value for role in AdminRole], required=True)
    args = parser.parse_args()
    try:
        principal = get_admin_user_use_case().set_role(args.username, args.role)
    except AdminError as error:
        sys.exit(error.message)
    print(f"등급 변경됨: {principal.username} ({principal.role})")


if __name__ == "__main__":
    main()
