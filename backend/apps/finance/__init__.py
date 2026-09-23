"""finance BC — 창업 자금 계획. "그래서 얼마가 필요한가"를 실측에서 출발시킨다.

**ERD 테이블이 없다.** §12 "1 테이블 = 1 프랙탈"의 의도적 예외이며 근거는 intent BC와 같다 —
계산은 상태가 없다. 프리필은 commerce·rent·shock·master를 읽을 뿐 아무것도 쓰지 않고, 계획 초안은
브라우저 sessionStorage에 산다(로그인이 없는데 서버 테이블은 이르다). 로그인이 생기면 `finance_plan`
테이블과 함께 11파일 세트로 승격한다. 설계서 `docs/superpowers/specs/2026-09-23-finance-plan-design.md`.

읽기 방향은 finance → commerce·rent·shock·master 단방향이며 cross-BC 접근은 게이트웨이 안에서만 한다.
"""
