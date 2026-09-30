import re
import secrets

_DEVICE_ID = re.compile(r"[A-Za-z0-9_-]{22}")


def new_device_id() -> str:
    return secrets.token_urlsafe(16)


def is_device_id(value: str | None) -> bool:
    return value is not None and _DEVICE_ID.fullmatch(value) is not None
