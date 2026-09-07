"""서울 열린데이터광장 학원·교습소(OA-20528, neisAcademyInfo) Driven Adapter.

- 엔드포인트: openapi.seoul.go.kr:8088/{key}/json/neisAcademyInfo/{start}/{end}/ (2026-09-07 실호출 검증)
- 제한: 일 1,000회·1회 1,000건 — 전량 ~26회 페이징 (call_count로 호출 수 추적)
- 좌표 없음: lat/lng NULL 적재 → SGIS 지오코딩 후속 대상. 자치구는 ADMDST_NM ↔ district.name 매핑
- 현행 스냅샷만 제공(갱신시점 필터 없음) → 매 실행 전량 수집, LOAD_DT를 source_updated_at으로 보존
"""

import calendar
import time
from collections.abc import Iterator
from datetime import date, datetime

import httpx

from apps.store.app.dtos.academy_course_dto import AcademyRecord
from apps.store.app.ports.output.academy_course_port import AcademyGatewayPort
from apps.store.domain.entities.academy_course_entity import AcademyCourse
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "http://openapi.seoul.go.kr:8088"
_SERVICE = "neisAcademyInfo"
_PAGE_SIZE = 1000  # API 최대값 (초과 시 ERROR-336)
_INDUSTRY_ID = "academy"

# 교습계열(FLD_NM) → industry_subcategory.subcategory_id (brainstorming §3.6 5축)
# 종합(대)·기타(대)·인문사회(대) 등 5축 밖 계열은 미매핑(None) — 분포는 수집 후 보고
_FIELD_SUBCATEGORIES = {
    "입시.검정 및 보습": "academy_exam",
    "예능(대)": "academy_arts",
    "기예(대)": "academy_arts",
    "국제화": "academy_language",
    "직업기술": "academy_vocational",
    "정보": "academy_vocational",
    "독서실": "academy_studyroom",
}

# 등록상태명(REG_STTS_NM) → status_code — 미지 상태는 원문 그대로 코드로 보존
_STATUS_CODES = {"개원": "open", "폐원": "closed", "휴원": "suspended"}


def _parse_ymd(value: str | None) -> date | None:
    """YYYYMMDD 방어 파싱 — 불량 일(day)은 월말로 클램프 (MOIS 게이트웨이 전례)."""
    text = (value or "").strip()
    if len(text) != 8 or not text.isdigit():
        return None
    year, month, day = int(text[:4]), int(text[4:6]), int(text[6:8])
    if not (1 <= month <= 12) or year < 1 or day < 1:
        return None
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _parse_fee_items(text: str) -> list[tuple[str, int | None]]:
    """수강료 내용(INDV_ATNLC_AMT_CN) → [(항목명, 금액)] — "초등영어A:150000, ..." 형식.

    금액이 숫자가 아니면 항목 전체를 이름으로 보존하고 금액은 None.
    """
    items: list[tuple[str, int | None]] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, _, amount = chunk.rpartition(":")
        amount = amount.strip().replace(",", "")
        if name.strip() and amount.isdigit():
            items.append((name.strip(), int(amount)))
        else:
            items.append((chunk, None))
    return items


def _build_courses(store_id: str, item: dict) -> list[AcademyCourse]:
    """수강료 공개 항목 우선, 없으면 교습과정 목록(TRNG_CRS_LIST_NM → TRNG_CRS_NM) — 원문 보존."""
    pairs = _parse_fee_items(item.get("INDV_ATNLC_AMT_CN") or "")
    if not pairs:
        names = [n.strip() for n in (item.get("TRNG_CRS_LIST_NM") or "").split(",") if n.strip()]
        if not names and (item.get("TRNG_CRS_NM") or "").strip():
            names = [item["TRNG_CRS_NM"].strip()]
        pairs = [(name, None) for name in dict.fromkeys(names)]  # 순서 유지 중복 제거
    return [
        AcademyCourse(
            course_id=f"{store_id}:{index}",
            store_id=store_id,
            course_name=name,
            tuition_fee=fee,
        )
        for index, (name, fee) in enumerate(pairs, start=1)
    ]


class SeoulAcademyGateway(AcademyGatewayPort):
    def __init__(self, district_codes: dict[str, str]) -> None:
        self._district_codes = district_codes  # 자치구명(ADMDST_NM) → district_code
        self.call_count = 0  # 일 1,000회 한도 규율 — CLI가 로그로 보고
        self.skipped_districts: dict[str, int] = {}  # 구 미매칭으로 버린 행

    def iter_academies(self) -> Iterator[AcademyRecord]:
        start = 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            while True:
                response = self._get_with_retry(
                    client,
                    f"{_BASE_URL}/{get_settings().seoul_open_data_api_key}/json/"
                    f"{_SERVICE}/{start}/{start + _PAGE_SIZE - 1}/",
                )
                self.call_count += 1
                payload = response.json().get(_SERVICE)
                if payload is None:  # 인증 실패·요청 오류는 서비스 키 없이 RESULT만 옴
                    raise RuntimeError(f"seoul academy API 오류: {response.text[:300]}")
                for item in payload.get("row") or []:
                    record = self._to_record(item)
                    if record is not None:
                        yield record
                if start + _PAGE_SIZE > int(payload["list_total_count"]):
                    return
                start += _PAGE_SIZE

    @staticmethod
    def _get_with_retry(client: httpx.Client, url: str, attempts: int = 3) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (MOIS 게이트웨이 전례)."""
        for attempt in range(attempts):
            try:
                response = client.get(url)
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

    def _to_record(self, item: dict) -> AcademyRecord | None:
        district_name = (item.get("ADMDST_NM") or "").strip()
        if not district_name:  # 자치구명 공란 행 실존 (2026-09-07 전량 중 40행) — 도로명주소에서 파싱
            parts = (item.get("ROAD_NM_ADDR") or "").split()
            if len(parts) >= 2 and parts[0].startswith("서울"):
                district_name = parts[1]
        district_code = self._district_codes.get(district_name)
        if district_code is None:  # 자치구 매칭 불가 — 버리고 건수 보고
            self.skipped_districts[district_name] = self.skipped_districts.get(district_name, 0) + 1
            return None
        # PEI_DSGN_NO(학원지정번호)는 서울 전역 유일 (2026-09-07 표본 2,915행 중복 0)
        store_id = f"{_INDUSTRY_ID}:seoul:{item['PEI_DSGN_NO']}"
        status_name = (item.get("REG_STTS_NM") or "").strip()
        load_date = _parse_ymd(item.get("LOAD_DT")) or date.today()
        store = Store(
            store_id=store_id,
            name=(item.get("PEI_NM") or "").strip(),
            industry_id=_INDUSTRY_ID,
            district_code=district_code,
            open_date=_parse_ymd(item.get("ESTBL_YMD")) or _parse_ymd(item.get("REG_YMD")),
            close_date=None,  # 원천에 폐원일자 필드 없음 — 상태는 status로 보존
            status_code=_STATUS_CODES.get(status_name, status_name),
            status_name=status_name,
            lat=None,  # 원천에 좌표 없음 — SGIS 지오코딩 후속 대상
            lng=None,
            source_updated_at=datetime(load_date.year, load_date.month, load_date.day),
            subcategory_id=_FIELD_SUBCATEGORIES.get((item.get("FLD_NM") or "").strip()),
        )
        return AcademyRecord(store=store, courses=_build_courses(store_id, item))
