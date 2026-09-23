"""neighborhood BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class MetricNotFoundError(Exception):
    """지원하지 않는 metric 이름."""
