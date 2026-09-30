"""취약점 스캐너가 흔히 두드리는 경로 — 이 서비스에는 존재하지 않는 PHP·설정 파일·VCS 경로."""

import re

_SCANNER_PATTERN = re.compile(
    r"(\.php\d?$|/\.env|/\.git/|/\.aws/|/\.ssh/|wp-(admin|login|content|includes)|phpmyadmin|/cgi-bin/|/actuator|/server-status|\.(bak|sql|swp)$)",
    re.IGNORECASE,
)


def is_scanner_probe(path: str) -> bool:
    return _SCANNER_PATTERN.search(path) is not None
