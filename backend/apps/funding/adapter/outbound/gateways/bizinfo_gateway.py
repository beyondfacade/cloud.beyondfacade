"""기업마당 지원사업 공고 Driven Adapter — 공공데이터포털판 "중소벤처기업부_중소기업 지원사업 공고 조회 서비스"(15157820).

이용조건: 공공누리 제3유형(출처표시·변경금지, 상업 이용 가능) — 화면에 "출처: 기업마당", 공고 문구는 원문 그대로.
기업마당 자체 API(bizinfoApi.do)는 저작권정책상 직접 수익·무단변경 금지·사전 협의 대상이라 바꿨다(BE v0.85.0).
필드명은 자체 API와 같다(2026-10-06 1,468건 대조, 값 차이 0) — 지원분야 중분류만 없다. 1,000건씩 페이징.
"""

import html
import re
from datetime import date, datetime

import httpx

from apps.funding.app.ports.output.funding_program_port import FundingSearchGatewayPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_keymaker_secret_manager import get_settings

_ENDPOINT = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"
_PAGE_SIZE = 1000
_TAG_PATTERN = re.compile(r"<[^>]+>")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def clean_summary(raw: str | None) -> str | None:
    """HTML 태그 제거 + 엔티티 복원 + 공백 정리. 변경금지라 자르지 않는다."""
    if not raw:
        return None
    text = html.unescape(_TAG_PATTERN.sub(" ", raw))
    return re.sub(r"\s+", " ", text).strip() or None


def page_items(body: dict) -> list[dict]:
    """포털 응답 body.items.item — 여러 건이면 목록, 한 건이면 dict, 결과가 없으면 빈 문자열이 온다."""
    items = body.get("items") or {}
    item = items.get("item") if isinstance(items, dict) else None
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def parse_period(raw: str | None) -> tuple[date | None, date | None]:
    """신청기간 원문 → (시작일, 마감일). 방어적 파싱.

    "2026-09-03 ~ 2026-09-17" → (시작, 마감) / 날짜 1개·"상시"·"예산 소진시" 등 → 마감 None.
    """
    if not raw:
        return None, None
    dates = []
    for token in _DATE_PATTERN.findall(raw):
        try:
            dates.append(date.fromisoformat(token))
        except ValueError:
            continue  # "2026-13-99" 같은 형식만 맞는 비정상 값 방어
    if len(dates) >= 2:
        return dates[0], dates[-1]
    if len(dates) == 1:
        return dates[0], None  # 마감 미상(공고문 참조 등) — 단정하지 않는다
    return None, None


def _parse_pnttm(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def to_entity(item: dict) -> FundingProgram | None:
    """실응답 1건 → 엔티티. 원천 ID·원문 링크 없는 항목은 버린다 (dedup·원문 인용 불가)."""
    program_id = item.get("pblancId")
    url = item.get("pblancUrl")
    if not program_id or not url:
        return None
    apply_period = (item.get("reqstBeginEndDe") or "").strip()
    apply_begin, deadline = parse_period(apply_period)
    return FundingProgram(
        program_id=program_id,
        source="bizinfo",
        title=(item.get("pblancNm") or "").strip(),
        org=(item.get("jrsdInsttNm") or "").strip(),
        url=url,
        apply_period=apply_period,
        exec_org=item.get("excInsttNm") or None,
        field_category=item.get("pldirSportRealmLclasCodeNm") or None,
        field_subcategory=item.get("pldirSportRealmMlsfcCodeNm") or None,
        target_text=item.get("trgetNm") or None,
        hashtags=item.get("hashtags") or None,
        apply_begin=apply_begin,
        deadline=deadline,
        summary=clean_summary(item.get("bsnsSumryCn")),
        posted_at=_parse_pnttm(item.get("creatPnttm")),
        source_updated_at=_parse_pnttm(item.get("updtPnttm")),
    )


class BizinfoGateway(FundingSearchGatewayPort):
    def fetch_all(self) -> list[FundingProgram]:
        items: list[dict] = []
        page = 1
        while True:
            response = httpx.get(
                _ENDPOINT,
                params={
                    "serviceKey": get_settings().data_go_kr_api_key,
                    "pageNo": page,
                    "numOfRows": _PAGE_SIZE,
                    "dataType": "json",
                },
                timeout=60,
            )
            response.raise_for_status()
            body = response.json()["response"]["body"]
            batch = page_items(body)
            items += batch
            if not batch or len(items) >= int(body.get("totalCount") or 0):
                break
            page += 1
        return [entity for entity in (to_entity(item) for item in items) if entity is not None]
