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
    childcare_api_key: str = ""  # 어린이집정보공개포털 운영계정 키 (일 1,000회)
    sgis_service_id: str = ""  # SGIS consumer_key (토큰 4h)
    sgis_security_key: str = ""  # SGIS consumer_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
