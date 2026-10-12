from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.auth import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    JWT_SECRET_KEY,
    create_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Авторизация"])


class SLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class SLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str


@router.post("/login", response_model=SLoginResponse)
async def login(data: SLoginRequest) -> SLoginResponse:
    if not JWT_SECRET_KEY or not ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=500,
            detail="Авторизация не настроена на сервере",
        )

    # Намеренно не разделяем «нет такого юзера» и «неверный пароль»,
    # чтобы не давать подсказок атакующему.
    if data.username != ADMIN_USERNAME or not verify_password(
        data.password, ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    token, expires_in = create_access_token(data.username)
    return SLoginResponse(
        access_token=token,
        expires_in=expires_in,
        username=data.username,
    )