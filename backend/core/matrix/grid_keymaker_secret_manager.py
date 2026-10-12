"""전역 Secret 매니저 — .env / 환경변수를 단일 창구로 제공한다.

우선순위: OS 환경변수(도커 컴포즈 주입) > backend/.env (로컬 실행).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    db_pool_size: int = 5  # SQLAlchemy 기본값 — k8s에선 파드 수 × (풀 + 오버플로)가 DB max_connections를 넘지 않게 env로 조절
    db_max_overflow: int = 10
    naver_ncp_api_key_id: str = ""
    naver_ncp_api_key: str = ""
    data_go_kr_api_key: str = ""
    seoul_open_data_api_key: str = ""
    ecos_api_key: str = ""
    rone_api_key: str = ""
    vworld_api_key: str = ""
    # 브이월드 인증키에 등록된 서비스URL — 데이터·WFS API는 domain 불일치 시 INCORRECT_KEY
    vworld_service_domain: str = "beyondfacade.cloud"
    gemini_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"  # 호스트 로컬 기본값 — 컨테이너는 compose가 host.docker.internal로 덮어쓴다
    anthropic_api_key: str = ""  # RAG 평가셋 1차 판정(judge_evalset)에만 쓴다 — 운영 경로엔 없음
    childcare_api_key: str = ""  # 어린이집정보공개포털 운영계정 키 (일 1,000회)
    sgis_service_id: str = ""  # SGIS consumer_key (토큰 4h)
    sgis_security_key: str = ""  # SGIS consumer_secret
    admin_cookie_secure: bool = False  # 관리자 세션 쿠키 Secure — HTTPS 배포에서는 true
    # 운영은 프론트(www.)와 API(api.)가 다른 호스트다 (serverplan Phase 6-4). 기본값은 로컬(같은 origin 프록시) 동작
    cors_allow_origins: str = "http://localhost:3200,http://127.0.0.1:3200"  # 쉼표 구분 — 운영 https://www.beyondfacade.cloud
    cookie_domain: str = ""  # 관리자 쿠키 Domain — 운영 beyondfacade.cloud(www 미들웨어가 api가 준 쿠키를 본다). 비우면 요청 호스트만
    frontend_origin: str = ""  # 구글 로그인 왕복 뒤 돌아갈 프론트 — 운영 https://www.beyondfacade.cloud. 비우면 상대 경로
    google_client_id: str = ""  # 구글 로그인 OAuth 클라이언트 — 둘 중 하나라도 비면 구글 버튼을 숨긴다
    google_client_secret: str = ""
    # 구글 콘솔 '승인된 리디렉션 URI'와 글자 하나까지 같아야 한다 — 프론트 origin의 /api/backend 프록시 경유
    google_redirect_uri: str = "http://localhost:3200/api/backend/admin/auth/google/callback"
    llm_mode: str = "live"  # live | fake — fake는 부하 테스트 컨테이너 전용(고정 지연 가짜 LLM, testplan §7-4)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
