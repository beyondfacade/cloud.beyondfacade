from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    """요청을 보낸 쪽 — IP와 브라우저마다 발급한 디바이스 ID(쿠키)."""

    ip: str | None
    device_id: str | None = None
    user_agent: str | None = None
