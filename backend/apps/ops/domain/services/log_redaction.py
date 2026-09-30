"""수집기 로그를 화면에 내보내기 전 비밀값 가림 — 공공데이터 serviceKey·API 키·DB 접속 비밀번호가 URL이나 오류 메시지에 섞여 나온다."""

import re

MASK = "***"

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # 베어러가 먼저 — 아래 키 규칙은 `Authorization: Bearer x`에서 'Bearer'만 가리고 토큰을 남긴다
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), rf"\1{MASK}"),
    # ?serviceKey=abc / api_key: abc / "token": "abc" / password=abc
    (
        re.compile(
            r"(?i)((?:service_?key|api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|client[_-]?secret"
            r"|password|passwd|pwd|authorization)[\"']?\s*[:=]\s*[\"']?)([^\s\"'&,;}]+)"
        ),
        rf"\1{MASK}",
    ),
    (re.compile(r"(://[^:/\s@]+:)[^@\s]+(@)"), rf"\1{MASK}\2"),  # postgresql://user:pass@host
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"), MASK),  # Google API 키 형태
)


def redact(line: str) -> str:
    for pattern, replacement in _RULES:
        line = pattern.sub(replacement, line)
    return line
