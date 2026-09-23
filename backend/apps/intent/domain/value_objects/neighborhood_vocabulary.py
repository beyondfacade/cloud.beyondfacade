"""동네 유형·시간대 블록의 한국어 어휘 — 리포트 문장을 만들 때 쓴다.

metric BC가 판정을, 프론트엔드가 화면 표기를 각자 갖는다. agent는 LLM에 넣을 **문장**을 만드는
쪽이라 이름이 필요하다. BC를 가로지르는 중복을 감수하고 각자 갖는 것은 `quarter_dimension.py`
전례와 같은 판단이다 — 값 객체는 도메인이라 전역 `core/`에 둘 수 없고(§11) BC 독립성이 중복
제거보다 우선이다. 유형 이름을 바꾸면 여기와 `apps/agent/.../neighborhood_vocabulary.py`·`frontend/src/shared/neighborhood.ts` 셋 다 고친다.
"""

NEIGHBORHOOD_TYPE_NAMES: dict[str, str] = {
    "office": "낮 인구 우위형",
    "campus": "대학가형",
    "dining": "먹자·나들이형",
    "hub": "생활 중심형",
    "residential": "주거형",
    "mixed": "혼합형",
}

# 6구간을 4블록으로 묶은 것 — 괄호의 시간은 원천 구간 경계다
TIME_BLOCK_NAMES: dict[str, str] = {
    "morning": "아침(06~11시)",
    "day": "낮(11~17시)",
    "evening": "저녁(17~21시)",
    "night": "밤(21~06시)",
}

TIME_LABEL_NAMES: dict[str, str] = {**TIME_BLOCK_NAMES, "flat": "하루 종일 고르게"}

FACILITY_TYPE_NAMES: dict[str, str] = {
    "airport": "공항",
    "bank": "은행",
    "bus_stop": "버스정거장",
    "bus_terminal": "버스터미널",
    "department_store": "백화점",
    "elementary_school": "초등학교",
    "general_hospital": "종합병원",
    "government": "관공서",
    "high_school": "고등학교",
    "hospital": "병원",
    "kindergarten": "유치원",
    "lodging": "숙박시설",
    "middle_school": "중학교",
    "pharmacy": "약국",
    "subway_station": "지하철역",
    "supermarket": "슈퍼마켓",
    "theater": "극장",
    "train_station": "기차역",
    "university": "대학교",
}


def type_name(code: str | None) -> str | None:
    return None if code is None else NEIGHBORHOOD_TYPE_NAMES.get(code, code)


def block_name(code: str | None) -> str | None:
    return None if code is None else TIME_BLOCK_NAMES.get(code, code)


def label_name(code: str | None) -> str | None:
    return None if code is None else TIME_LABEL_NAMES.get(code, code)


def facility_name(code: str) -> str:
    return FACILITY_TYPE_NAMES.get(code, code)

# 원천 6구간의 한국어 — "언제 돈이 도나"에 답할 때 쓴다
HOUR_BAND_NAMES: dict[str, str] = {
    "00_06": "새벽(00~06시)",
    "06_11": "아침(06~11시)",
    "11_14": "점심(11~14시)",
    "14_17": "오후(14~17시)",
    "17_21": "저녁(17~21시)",
    "21_24": "밤(21~24시)",
}


def hour_band_name(code: str) -> str:
    return HOUR_BAND_NAMES.get(code, code)
