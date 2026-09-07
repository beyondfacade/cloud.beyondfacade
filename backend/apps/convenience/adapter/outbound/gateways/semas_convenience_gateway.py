"""소진공 상가정보(sdsc2) 편의점 Driven Adapter.

- 엔드포인트: apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong (2026-09-07 실호출 검증)
- 필터: indsSclsCd=G20405(체인화 편의점) 고정, divId=adongCd
- adongCd 8자리 = region_code 앞 8자리 (427개 행정동 프리픽스 유일 — DB 실측),
  응답 좌표는 WGS84 원값(변환 불요, 역삼1동 149건 채움 100%)
- numOfRows=1000 실호출 검증 (역삼1동 149건 1페이지 수신) — 페이징은 방어적으로 유지
- 인증: DATA_GO_KR_API_KEY (일 10,000회 한도 — 서울 전량 427회/스냅샷 = 4.3%)
"""

import time

from collections.abc import Iterator

import httpx

from apps.convenience.app.ports.output.convenience_store_port import ConvenienceGatewayPort
from apps.convenience.domain.entities.convenience_store_entity import (
    ConvenienceStore,
    extract_brand,
)
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
_PAGE_SIZE = 1000
_INDS_SCLS_CD = "G20405"  # 소매 > 종합 소매 > 편의점 (KSIC G47122 체인화 편의점)


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value), 7)


class SemasConvenienceGateway(ConvenienceGatewayPort):
    def __init__(self) -> None:
        self._key = get_settings().data_go_kr_api_key
        self.call_count = 0  # 호출량 규율 — CLI가 로그로 보고

    def iter_stores(self, region_code: str) -> Iterator[ConvenienceStore]:
        params: dict[str, str | int] = {
            "serviceKey": self._key,
            "divId": "adongCd",
            "key": region_code[:8],  # 행정동코드 8자리 (region_code 앞 8자리 유일 실측)
            "indsSclsCd": _INDS_SCLS_CD,
            "numOfRows": _PAGE_SIZE,
            "type": "json",
        }
        page = 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            while True:
                response = self._get_with_retry(client, _BASE_URL, {**params, "pageNo": page})
                self.call_count += 1
                try:
                    payload = response.json()
                except ValueError as error:  # 인증 오류 등은 XML로 옴
                    raise RuntimeError(
                        f"semas convenience API 비JSON 응답: {response.text[:300]}"
                    ) from error
                header = payload.get("header") or {}
                if (header.get("resultCode") or "") != "00":
                    raise RuntimeError(f"semas convenience API 오류: {response.text[:300]}")
                body = payload.get("body") or {}
                stdr_ym = str(header.get("stdrYm") or "").strip()
                for item in body.get("items") or []:
                    yield self._to_entity(item, region_code, stdr_ym)
                if page * _PAGE_SIZE >= int(body.get("totalCount") or 0):
                    return
                page += 1

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (MOIS 게이트웨이 전례)."""
        for attempt in range(attempts):
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as error:
                if error.response.status_code < 500 or attempt == attempts - 1:
                    raise
            except httpx.TimeoutException:
                if attempt == attempts - 1:
                    raise
            time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    @staticmethod
    def _to_entity(item: dict, region_code: str, stdr_ym: str) -> ConvenienceStore:
        name = (item.get("bizesNm") or "").strip()
        branch_name = (item.get("brchNm") or "").strip() or None
        return ConvenienceStore(
            store_id=item["bizesId"],
            name=name,
            branch_name=branch_name,
            brand=extract_brand(name, branch_name),
            region_code=region_code,  # 요청 행정동 그대로 — 응답 adongCd와 동일 (실측)
            lat=_to_float(item.get("lat")),
            lng=_to_float(item.get("lon")),
            road_address=(item.get("rdnmAdr") or "").strip() or None,
            jibun_address=(item.get("lnoAdr") or "").strip() or None,
            source_stdr_ym=stdr_ym,
        )
