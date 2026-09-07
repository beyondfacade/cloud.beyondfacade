"""기업마당(bizinfo) 지원사업정보 Open API Driven Adapter.

docs/api.md §5.2: 엔드포인트 bizinfo.go.kr/uss/rss/bizinfoApi.do, 자체 키(crtfcKey), JSON.
중앙부처+지자체+유관기관 공고 ~1,500건 상시 통합 — searchCnt 한 번으로 전량 수신 (페이징 불필요).
"""

import html
import re
from datetime import date, datetime

import httpx

from apps.funding.app.ports.output.funding_program_port import FundingSearchGatewayPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_keymaker_secret_manager import get_settings

_ENDPOINT = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
_SEARCH_CNT = 3000  # 상시 ~1,500건 — 여유분 포함 1회 호출 전량 수신
_TAG_PATTERN = re.compile(r"<[^>]+>")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_SUMMARY_MAX = 1000  # 요약 발췌 상한 — 본문 전문 저장 금지 (brainstorming §8.1)


def clean_summary(raw: str | None) -> str | None:
    """HTML 태그 제거 + 엔티티 복원 + 공백 정리 후 발췌."""
    if not raw:
        return None
    text = html.unescape(_TAG_PATTERN.sub(" ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_SUMMARY_MAX] or None


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
        response = httpx.get(
            _ENDPOINT,
            params={
                "crtfcKey": get_settings().bizinfo_api_key,
                "dataType": "json",
                "searchCnt": _SEARCH_CNT,
            },
            timeout=60,
        )
        response.raise_for_status()
        programs = []
        for item in response.json().get("jsonArray", []):
            entity = to_entity(item)
            if entity is not None:
                programs.append(entity)
        return programs
