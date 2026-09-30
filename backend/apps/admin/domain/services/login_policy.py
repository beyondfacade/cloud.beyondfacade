from datetime import timedelta

# 같은 IP에서 이 창 안에 실패가 한도에 닿으면 비밀번호를 확인하지 않고 거절한다
THROTTLE_LIMIT = 10
THROTTLE_WINDOW = timedelta(minutes=10)
