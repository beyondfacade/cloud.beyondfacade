"""프로필 규칙 — 사진은 PNG·JPEG·WebP 1MB 이하(파일 앞머리로 판별), 전문 업종은 1~20자."""

MAX_AVATAR_BYTES = 1024 * 1024
MAX_SPECIALTY_LENGTH = 20


def avatar_media_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def avatar_problem(content: bytes) -> str | None:
    if not content:
        return "사진 파일이 비어 있습니다."
    if len(content) > MAX_AVATAR_BYTES:
        return "사진은 1MB 이하만 올릴 수 있습니다."
    if avatar_media_type(content) is None:
        return "PNG·JPG·WebP 사진만 올릴 수 있습니다."
    return None


def specialty_problem(specialty: str) -> str | None:
    if 1 <= len(specialty) <= MAX_SPECIALTY_LENGTH:
        return None
    return f"전문 업종은 1~{MAX_SPECIALTY_LENGTH}자여야 합니다."
