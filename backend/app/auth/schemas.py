from pydantic import BaseModel, EmailStr, Field, field_validator

from app.users.schemas import USERNAME_PATTERN, CurrentUserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=40)
    full_name: str = Field(min_length=1, max_length=120)
    university_id: str | None = Field(default=None, max_length=50)
    chesscom_username: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str) -> str:
        normalized = username.strip()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Username must be 3-40 characters and use letters, numbers, or underscores"
            )
        return normalized

    @field_validator("full_name", "university_id", "chesscom_username")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    tokens: TokenResponse
    user: CurrentUserResponse


class LogoutResponse(BaseModel):
    revoked: bool
