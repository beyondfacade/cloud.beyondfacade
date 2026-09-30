"""쿼리 파라미터 허용값 — Literal[24, 168]은 쿼리 문자열 '168'을 int로 바꾸지 않아 422가 난다."""

from collections.abc import Collection

from pydantic import AfterValidator

HOST_HISTORY_HOURS = (1, 6, 24, 168)
USAGE_SERIES_HOURS = (24, 168)


def one_of(allowed: Collection[int]) -> AfterValidator:
    def check(value: int) -> int:
        if value not in allowed:
            raise ValueError(f"허용값: {sorted(allowed)}")
        return value

    return AfterValidator(check)
