"""intent BC — 한 문장을 받아 동·업종·예산을 뽑고 한 줄 진단을 붙이는 관문.

**ERD 테이블이 없다.** §12 "1 테이블 = 1 프랙탈"의 의도적 예외다. 파싱은 상태가 없다 —
마스터(`region`·`district`·`industry`)와 파생(`region_profile_quarter`·`region_industry_hour_gap_quarter`)을
읽을 뿐 아무것도 쓰지 않는다. 그래서 entity·orm·orm_mapper·repository가 없고, 대신 읽기 포트 셋
(마스터 사전·파생 사실·LLM 추출)과 그 게이트웨이가 있다.

"사람들이 뭘 묻는가"를 남기는 `intent_log`는 값이 있지만 지금은 만들지 않는다. 되묻기 비율이
궁금해지면 그때 테이블과 함께 11파일 세트로 승격한다 (설계서 `2026-09-23-chat-first-direction.md` §3).
"""
