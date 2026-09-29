"""국토부 아파트 매매 실거래가 Driven Adapter — apis.data.go.kr/1613000/RTMSDataSvcAptTrade (파일럿 9/29, 설계서 §11).
LAWD_CD(시군구 5자리) × DEAL_YMD(월) 반복 호출, numOfRows 1000 페이지. 최근 1~2개월은 신고기한(30일) 탓에 미완결."""

import time
import xml.etree.ElementTree as ET
from collections import Counter

import httpx

from core.matrix.grid_keymaker_secret_manager import get_settings

_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
_PAGE_SIZE = 1000
_OK_CODES = frozenset({"00", "000"})


class MolitApiError(RuntimeError):
    """정상 코드가 아닌 응답 — 활용신청 미승인(SERVICE_KEY_IS_NOT_REGISTERED_ERROR)·트래픽 초과 등."""


def count_by_legal_dong(xml_text: str) -> tuple[Counter[str], int]:
    root = ET.fromstring(xml_text)
    code = (root.findtext("header/resultCode") or "").strip()
    if code not in _OK_CODES:
        reason = root.findtext(".//returnAuthMsg") or root.findtext("header/resultMsg") or "응답 코드 없음"
        raise MolitApiError(f"{code or '-'}: {reason.strip()}")
    counts = Counter((item.findtext("umdNm") or "").strip() for item in root.iter("item"))
    counts.pop("", None)
    return counts, int(root.findtext("body/totalCount") or 0)


class MolitAptTradeGateway:
    def month_counts(self, district_code: str, deal_ym: str) -> Counter[str]:
        """한 구·한 달의 법정동별 매매 건수 (페이지 전부)."""
        counts: Counter[str] = Counter()
        page = 1
        with httpx.Client(timeout=30) as client:
            while True:
                response = client.get(_URL, params={
                    "serviceKey": get_settings().data_go_kr_api_key, "LAWD_CD": district_code,
                    "DEAL_YMD": deal_ym, "pageNo": page, "numOfRows": _PAGE_SIZE,
                })
                response.raise_for_status()
                page_counts, total = count_by_legal_dong(response.text)
                counts.update(page_counts)
                if page * _PAGE_SIZE >= total:
                    return counts
                page += 1
                time.sleep(0.2)
