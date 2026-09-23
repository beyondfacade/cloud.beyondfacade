"""intent BC 도메인 예외 — 라우터가 잡아 에러 바디로 변환한다."""


class IntentTextEmptyError(Exception):
    """빈 문장 — 파싱할 것이 없다."""


class RegionNotFoundError(Exception):
    """마스터에 없는 행정동 코드 (두 번째 요청 형태)."""


class IndustryNotFoundError(Exception):
    """마스터에 없는 업종 (두 번째 요청 형태)."""
