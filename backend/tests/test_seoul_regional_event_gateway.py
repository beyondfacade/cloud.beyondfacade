"""서울 열린데이터광장 지역 이벤트 게이트웨이 — HTTP는 MockTransport, 지오코더는 Fake (경계만 모킹).

행 픽스처는 2026-10-06 실응답 표본에서 필요한 키만 그대로 옮겼다.
"""

import httpx

from apps.shock.adapter.outbound.gateways.seoul_regional_event_gateway import (
    ApartmentGateway,
    LargeStoreGateway,
    RedevelopmentGateway,
)
from apps.store.app.ports.output.geocoding_port import GeocodingGatewayPort


def _client(service: str, pages: list[list[dict]], total: int, calls: list[str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        page = pages[len(calls) - 1]
        return httpx.Response(200, json={service: {"list_total_count": total, "row": page}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_large_store_gateway_converts_5174_and_skips_ssm():
    rows = [
        {"MGTNO": "2004315010007500033", "BPLCNM": "(주)이마트 가양점", "UPTAENM": "대형마트",
         "JPSENM": "대규모점포", "APVPERMYMD": "1999-12-28", "DCBYMD": "2022-09-27",
         "X": "187761.194273879    ", "Y": "450640.214509068    "},
        {"MGTNO": "2026323029107500004", "BPLCNM": "GS THE FRESH 송파석촌역점", "UPTAENM": "구분없음",
         "JPSENM": "준대규모점포", "APVPERMYMD": "2026-08-18", "DCBYMD": "          ",
         "X": "209134.86711622     ", "Y": "444864.58985226     "},
    ]
    calls: list[str] = []
    gateway = LargeStoreGateway(client=_client("LOCALDATA_082501", [rows], 2, calls))
    [located] = gateway.fetch_located_events()
    assert located.event.name == "(주)이마트 가양점 폐업"
    assert 37.55 < located.lat < 37.58 and 126.83 < located.lng < 126.87  # 강서구 가양동
    assert calls[0].endswith("/json/LOCALDATA_082501/1/1000/")


def test_apartment_gateway_pages_until_total_count():
    big = {"APT_CD": "A10025638", "APT_NM": "래미안길음센터피스", "TNOHSH": 2352.0,
           "USE_APRV_YMD": "2019-11-29 00:00:00.0", "XCRD": "127.027970717", "YCRD": "37.609757966"}
    no_coordinate = {**big, "APT_CD": "A2", "XCRD": "", "YCRD": ""}
    calls: list[str] = []
    gateway = ApartmentGateway(client=_client("OpenAptInfo", [[big], [no_coordinate]], 1001, calls))
    located = gateway.fetch_located_events()
    assert [c.split("/json/")[1] for c in calls] == ["OpenAptInfo/1/1000/", "OpenAptInfo/1001/2000/"]
    assert [(l.event.event_id, l.lat, l.lng) for l in located] == [
        ("regional-apt-movein-A10025638", 37.609757966, 127.027970717),
        ("regional-apt-movein-A2", None, None),
    ]


class FakeGeocoder(GeocodingGatewayPort):
    def __init__(self, known: dict[str, tuple[float, float]]) -> None:
        self._known = known
        self.asked: list[str] = []

    def geocode(self, address: str) -> tuple[float, float] | None:
        self.asked.append(address)
        return self._known.get(address)


def test_redevelopment_gateway_geocodes_jibun_then_road_once_per_zone():
    row = {"CODE": "2493", "DISTRICT": "중구", "ZONE_NM": "세운6-3-3", "JIBUN_ADDR": "을지로4가310-2",
           "ROAD_ADDR": "을지로22길11", "BIZ_TYPE": "도시정비형 재개발",
           "MIGRATION_START_YMD": "2020-12-01", "MIGRATION_END_YMD": "2021-05-25",
           "CONSTRUCTION_START_YMD": "2021-07-02"}
    unknown = {**row, "CODE": "9", "JIBUN_ADDR": "어딘가1", "ROAD_ADDR": ""}
    geocoder = FakeGeocoder({"서울특별시 중구 을지로22길11": (37.5659, 126.9963)})
    gateway = RedevelopmentGateway(geocoder, client=_client("TbSeoulRedevStatus", [[row, unknown]], 2, []))
    located = gateway.fetch_located_events()
    assert [(l.event.event_id, l.lat) for l in located] == [
        ("regional-redev-migration-2493", 37.5659),
        ("regional-redev-construction-2493", 37.5659),
        ("regional-redev-migration-9", None),
        ("regional-redev-construction-9", None),
    ]
    assert geocoder.asked == [
        "서울특별시 중구 을지로4가310-2",
        "서울특별시 중구 을지로22길11",
        "서울특별시 중구 어딘가1",  # 도로명 공란 — 지번 1회만
    ]
