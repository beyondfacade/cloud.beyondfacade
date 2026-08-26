"""브이월드 경계 API Driven Adapter (2026-08-26 실호출 검증).

- 행정동 경계: WFS lt_c_cademd — 통계청 코드(adm_cd) 기반, 서울 426동 1회 수신 가능
- 법정동 경계: 데이터 API LT_C_ADEMD_INFO — 행정동 레이어에 없는 분동(용두동·신설동) 보충용
- 인증: key + domain(인증키에 등록된 서비스URL) 쿼리 파라미터 — 둘 다 일치해야 통과
- WFS 1.1.0 EPSG:4326의 BBOX는 위도,경도 축 순서 — FILTER(속성식)만 사용해 축 문제 회피
"""

import httpx

from core.matrix.grid_keymaker_secret_manager import get_settings

_WFS_URL = "https://api.vworld.kr/req/wfs"
_DATA_URL = "https://api.vworld.kr/req/data"
_TIMEOUT = 60.0
# 서울 행정동 필터 — 통계청 시도코드 prefix 11은 서울 고유
_SEOUL_FILTER = (
    '<Filter><PropertyIsLike wildCard="*" singleChar="." escape="!">'
    "<PropertyName>adm_cd</PropertyName><Literal>11*</Literal>"
    "</PropertyIsLike></Filter>"
)


class VworldBoundaryGateway:
    def __init__(self) -> None:
        settings = get_settings()
        self._key = settings.vworld_api_key
        self._domain = settings.vworld_service_domain

    def fetch_seoul_admin_dongs(self) -> list[dict]:
        """서울 전체 행정동 경계 GeoJSON Feature 목록 (1회 호출, 문서상 1,000피처 한도 내)."""
        response = httpx.get(
            _WFS_URL,
            params={
                "SERVICE": "WFS",
                "REQUEST": "GetFeature",
                "VERSION": "1.1.0",
                "TYPENAME": "lt_c_cademd",
                "FILTER": _SEOUL_FILTER,
                "SRSNAME": "EPSG:4326",
                "OUTPUT": "application/json",
                "MAXFEATURES": "1000",
                "key": self._key,
                "domain": self._domain,
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()  # 인증 실패 시 XML → json 파싱 에러로 즉시 드러남
        return body["features"]

    def fetch_legal_dong(self, emd_cd: str) -> dict:
        """법정동 1건의 경계 GeoJSON Feature (emd_cd 8자리 정확 일치)."""
        response = httpx.get(
            _DATA_URL,
            params={
                "service": "data",
                "request": "GetFeature",
                "data": "LT_C_ADEMD_INFO",
                "attrFilter": f"emd_cd:=:{emd_cd}",
                "crs": "EPSG:4326",
                "format": "json",
                "size": "1",
                "key": self._key,
                "domain": self._domain,
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()["response"]
        if body["status"] != "OK":
            raise RuntimeError(f"LT_C_ADEMD_INFO {emd_cd} 조회 실패: {body.get('error')}")
        return body["result"]["featureCollection"]["features"][0]
