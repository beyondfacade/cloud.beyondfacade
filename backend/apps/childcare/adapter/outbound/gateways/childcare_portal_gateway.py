"""어린이집정보공개포털 cpmsapi030(어린이집 기본정보) Driven Adapter.

- 엔드포인트: https://api.childcare.go.kr/mediate/rest/cpmsapi030/cpmsapi030/request
  (2026-09-17 운영키 실호출 검증 — http는 빈 응답, https만 동작)
- arcode = 시군구코드 5자리 = district_code. 1회 호출에 구 전체 시설 반환(강남 162건, 페이징 없음)
- 응답은 XML. 인증 실패도 HTTP 200 + <errcode>INFO-100</errcode> 본문으로 온다
- 인증: CHILDCARE_API_KEY (운영계정, 일 1,000회 — 서울 전량 25회/스냅샷)
"""

import time
import xml.etree.ElementTree as ET
from datetime import date

import httpx

from apps.childcare.app.ports.output.childcare_center_port import ChildcareGatewayPort
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://api.childcare.go.kr/mediate/rest/cpmsapi030/cpmsapi030/request"


def _text(item: ET.Element, tag: str) -> str | None:
    return (item.findtext(tag) or "").strip() or None


def _date(item: ET.Element, tag: str) -> date | None:
    value = _text(item, tag)
    return date.fromisoformat(value) if value else None


def _float(item: ET.Element, tag: str) -> float | None:
    value = _text(item, tag)
    return float(value) if value else None


def _int(item: ET.Element, tag: str) -> int | None:
    value = _text(item, tag)
    return int(float(value)) if value else None


class ChildcarePortalGateway(ChildcareGatewayPort):
    def __init__(self) -> None:
        self._key = get_settings().childcare_api_key
        self.call_count = 0  # 호출량 규율 — CLI가 로그로 보고 (일 1,000회 한도)

    def fetch_centers(self, district_code: str) -> list[ChildcareCenter]:
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            response = self._get_with_retry(
                client, _BASE_URL, {"key": self._key, "arcode": district_code}
            )
        self.call_count += 1
        root = ET.fromstring(response.text)
        if root.find("errcode") is not None:
            raise RuntimeError(
                f"childcare API 오류: {root.findtext('errcode')} {root.findtext('errmsg')}"
            )
        return [self._to_entity(item, district_code) for item in root.findall("item")]

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (convenience 게이트웨이 전례)."""
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
    def _to_entity(item: ET.Element, district_code: str) -> ChildcareCenter:
        return ChildcareCenter(
            center_id=item.findtext("stcode").strip(),
            name=_text(item, "crname"),
            type_name=_text(item, "crtypename"),
            status_name=_text(item, "crstatusname"),
            district_code=district_code,  # 요청 arcode 그대로 (응답 sigunname과 일치 실측)
            address=_text(item, "craddr"),
            zipcode=_text(item, "zipcode"),
            tel=_text(item, "crtelno"),
            lat=_float(item, "la"),
            lng=_float(item, "lo"),
            approved_on=_date(item, "crcnfmdt"),
            paused_from=_date(item, "crpausebegindt"),
            paused_until=_date(item, "crpauseenddt"),
            abolished_on=_date(item, "crabldt"),
            stat=ChildcareCenterStat(
                base_date=_date(item, "datastdrdt"),
                capacity=_int(item, "crcapat"),
                child_count=_int(item, "crchcnt"),
                waiting_count=_int(item, "EW_CNT_TOT"),
                class_count=_int(item, "CLASS_CNT_TOT"),
                staff_count=_int(item, "chcrtescnt"),
            ),
        )
