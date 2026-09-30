from datetime import timedelta

# 같은 IP에서 이 창 안에 실패가 한도에 닿으면 비밀번호를 확인하지 않고 거절한다
THROTTLE_LIMIT = 10
THROTTLE_WINDOW = timedelta(minutes=10)

# 공개 가입 — 같은 IP에서 이 창 안에 가입이 한도에 닿으면 더 만들지 않는다 (계정 대량 생성 방지)
SIGNUP_LIMIT = 5
SIGNUP_WINDOW = timedelta(hours=1)
