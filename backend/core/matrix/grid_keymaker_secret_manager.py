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
    naver_ncp_api_key_id: str = ""
    naver_ncp_api_key: str = ""
    data_go_kr_api_key: str = ""
    bizinfo_api_key: str = ""
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
    google_client_id: str = ""  # 구글 로그인 OAuth 클라이언트 — 둘 중 하나라도 비면 구글 버튼을 숨긴다
    google_client_secret: str = ""
    # 구글 콘솔 '승인된 리디렉션 URI'와 글자 하나까지 같아야 한다 — 프론트 origin의 /api/backend 프록시 경유
    google_redirect_uri: str = "http://localhost:3200/api/backend/admin/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
