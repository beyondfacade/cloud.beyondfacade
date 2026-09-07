"""master BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class RegionNotFoundError(Exception):
    """region 마스터에 등록되지 않은 행정동코드."""
