from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleIdentityDto:
    """구글 ID 토큰에서 꺼낸 신원 — sub가 영구 식별자, email은 바뀔 수 있다."""

    sub: str
    email: str
    email_verified: bool
