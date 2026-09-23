"""업종 동의어 — 마스터 `industry` 10종에 대해 사람이 쓰는 말. 매칭 결과는 industry_id여야 한다.

대구 분화본의 사전을 참고하되 우리 10종에 맞췄다(restaurant는 우리 마스터에 없다).
긴 표현이 먼저 검사되도록 소비하는 쪽이 길이순으로 정렬한다.
"""

INDUSTRY_SYNONYMS: dict[str, str] = {
    "카페": "cafe", "커피": "cafe", "디저트": "cafe", "베이커리": "cafe", "커피숍": "cafe",
    "편의점": "convenience_store", "편의점을": "convenience_store",
    "미용실": "hair_salon", "헤어": "hair_salon", "헤어샵": "hair_salon", "미용": "hair_salon",
    "네일": "hair_salon",
    "노래방": "karaoke", "코인노래방": "karaoke", "노래연습장": "karaoke",
    "PC방": "pc_bang", "피시방": "pc_bang", "피씨방": "pc_bang", "pc방": "pc_bang",
    "헬스장": "gym", "헬스": "gym", "피트니스": "gym", "체육관": "gym", "짐": "gym",
    "당구장": "billiard", "포켓볼": "billiard", "당구": "billiard",
    "부동산": "real_estate", "공인중개": "real_estate", "중개사무소": "real_estate",
    "학원": "academy", "교습소": "academy", "과외": "academy", "공부방": "academy",
    "어린이집": "childcare", "유치원": "childcare", "보육": "childcare",
}
