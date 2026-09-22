"""SGIS 통계지리정보 OpenAPI Driven Adapter — 주소 지오코딩.

- 인증: consumer_key/secret → accessToken (유효 4시간)
- 지오코딩: OpenAPI3/addr/geocode.json — 응답 X/Y는 UTM-K(EPSG:5179)
- 변환: EPSG:5179 → WGS84 (웹 지도·assign_regions 정합)
- 문서: https://sgis.mods.go.kr/developer (권고 일 5만 회)
"""

import time

import httpx
from pyproj import Transformer

from apps.store.app.ports.output.geocoding_port import GeocodingGatewayPort
from core.matrix.grid_keymaker_secret_manager import get_settings

_AUTH_URL = "https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json"
_GEOCODE_URL = "https://sgisapi.mods.go.kr/OpenAPI3/addr/geocode.json"
# 토큰 만료 여유(초) — 문서상 4h; 갱신 직전에 미리 재발급
_TOKEN_SKEW_SEC = 60
_TRANSFORMER = Transformer.from_crs(5179, 4326, always_xy=True)
# 서울 근방 대략 범위 — 변환 이상값 방어
_SEOUL_LAT = (37.0, 38.0)
_SEOUL_LNG = (126.0, 128.0)


class SgisGeocodingGateway(GeocodingGatewayPort):
    def __init__(self, client: httpx.Client | None = None) -> None:
        settings = get_settings()
        self._consumer_key = settings.sgis_service_id
        self._consumer_secret = settings.sgis_security_key
        self._client = client or httpx.Client(timeout=httpx.Timeout(30, connect=10))
        self._owns_client = client is None
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self.call_count = 0

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def geocode(self, address: str) -> tuple[float, float] | None:
        address = (address or "").strip()
        if not address:
            return None
        if not self._consumer_key or not self._consumer_secret:
            raise RuntimeError(
                "SGIS_SERVICE_ID / SGIS_SECURITY_KEY 미설정 — backend/.env 확인"
            )
        token = self._access_token()
        response = self._client.get(
            _GEOCODE_URL,
            params={
                "accessToken": token,
                "address": address,
                "pagenum": 0,
                "resultcount": 1,
            },
        )
        self.call_count += 1
        response.raise_for_status()
        payload = response.json()
        err = str(payload.get("errCd", ""))
        if err == "-100":  # 검색결과 없음
            return None
        if err not in ("0", ""):
            # 토큰 만료 등 — 1회 재발급 후 재시도
            if err in ("-401", "-1001", "-200"):
                self._token = None
                token = self._access_token()
                response = self._client.get(
                    _GEOCODE_URL,
                    params={
                        "accessToken": token,
                        "address": address,
                        "pagenum": 0,
                        "resultcount": 1,
                    },
                )
                self.call_count += 1
                response.raise_for_status()
                payload = response.json()
                err = str(payload.get("errCd", ""))
                if err == "-100":
                    return None
                if err not in ("0", ""):
                    raise RuntimeError(f"SGIS geocode 오류 errCd={err}: {payload}")
            else:
                raise RuntimeError(f"SGIS geocode 오류 errCd={err}: {payload}")

        result = payload.get("result") or {}
        rows = result.get("resultdata") or []
        if not rows:
            return None
        row = rows[0]
        try:
            x = float(row["x"] if "x" in row else row["X"])
            y = float(row["y"] if "y" in row else row["Y"])
        except (KeyError, TypeError, ValueError):
            return None
        lng, lat = _TRANSFORMER.transform(x, y)
        if not (_SEOUL_LAT[0] <= lat <= _SEOUL_LAT[1] and _SEOUL_LNG[0] <= lng <= _SEOUL_LNG[1]):
            return None
        return lat, lng

    def _access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - _TOKEN_SKEW_SEC:
            return self._token
        response = self._client.get(
            _AUTH_URL,
            params={
                "consumer_key": self._consumer_key,
                "consumer_secret": self._consumer_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        err = str(payload.get("errCd", "0"))
        if err not in ("0", ""):
            raise RuntimeError(f"SGIS auth 오류 errCd={err}: {payload}")
        result = payload.get("result") or {}
        token = result.get("accessToken")
        if not token:
            raise RuntimeError(f"SGIS auth 토큰 없음: {payload}")
        # accessTimeout = epoch seconds of expiry (문서)
        timeout_raw = result.get("accessTimeout")
        try:
            expires = float(timeout_raw)
            # 일부 응답은 잔여 초로 오기도 함 — epoch이면 1e9 이상
            if expires < 1_000_000_000:
                expires = now + expires
        except (TypeError, ValueError):
            expires = now + 4 * 3600
        self._token = token
        self._token_expires_at = expires
        return token
