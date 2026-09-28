"""verdict BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class IndustryNotFoundError(Exception):
    """판정 대상 업종이 아니다 (마스터 미등록이거나 EXCLUDED_INDUSTRIES)."""
