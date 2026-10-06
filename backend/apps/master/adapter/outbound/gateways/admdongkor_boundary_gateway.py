"""행정동 경계 Driven Adapter — vuski/admdongkor 버전 고정 GeoJSON.

- 원자료: 통계청 SGIS 행정동 경계(공공데이터포털 15129688 "이용허락범위 제한 없음"), admdongkor 가공분은 CC BY 4.0
  (저장소 LICENSE-DATA). 브이월드 경계는 약관상 사전 승낙 없는 저장·재배포가 안 돼 바꿨다.
- ver20260701: 전국 3,558동·서울 427동, adm_cd2 = 행안부 10자리(region_code), EPSG:4326, 2025-07 용신동 분동 반영
"""

import httpx

VERSION = "ver20260701"
_URL = f"https://raw.githubusercontent.com/vuski/admdongkor/master/{VERSION}/HangJeongDong_{VERSION}.geojson"
_TIMEOUT = 120.0
_SEOUL_PREFIX = "11"  # 행안부 시도코드 — 서울


class AdmdongkorBoundaryGateway:
    def fetch_seoul_admin_dongs(self) -> list[dict]:
        """서울 행정동 경계 GeoJSON Feature 목록 (전국 파일 1회 내려받아 서울만)."""
        response = httpx.get(_URL, timeout=_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        return [f for f in response.json()["features"] if str(f["properties"]["adm_cd2"]).startswith(_SEOUL_PREFIX)]
