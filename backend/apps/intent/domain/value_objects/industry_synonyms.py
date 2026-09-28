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
    # 음식 7종 (2026-09-28) — restaurant_other 는 동의어 없음: 관문에서 고를 수 없는 비노출 업종
    "한식": "korean_food", "한식당": "korean_food", "밥집": "korean_food", "국밥": "korean_food",
    "백반": "korean_food", "고깃집": "korean_food", "삼겹살": "korean_food", "찌개": "korean_food",
    "중식": "chinese_food", "중국집": "chinese_food", "중식당": "chinese_food", "짜장면": "chinese_food",
    "일식": "japanese_food", "일식당": "japanese_food", "초밥": "japanese_food", "스시": "japanese_food",
    "횟집": "japanese_food", "라멘": "japanese_food", "이자카야": "japanese_food",
    "양식": "western_food", "양식당": "western_food", "파스타": "western_food", "레스토랑": "western_food",
    "피자": "western_food", "브런치": "western_food",
    "분식": "snack", "분식집": "snack", "김밥": "snack", "떡볶이": "snack",
    "치킨": "chicken", "치킨집": "chicken", "통닭": "chicken",
    "호프": "pub", "호프집": "pub", "술집": "pub", "주점": "pub", "포차": "pub", "맥주집": "pub",
}
