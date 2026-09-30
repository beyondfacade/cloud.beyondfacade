from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)  # 계정명 또는 이메일
    password: str = Field(min_length=1, max_length=256)


class SignupRequest(BaseModel):
    # 형식 규칙은 도메인이 판정해 INVALID_USERNAME·INVALID_EMAIL·WEAK_PASSWORD로 답한다
    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=512)


class AdminMeResponse(BaseModel):
    username: str
    role: str
    can_operate: bool


class AuthProvidersResponse(BaseModel):
    google: bool
