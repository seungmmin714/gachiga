from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt_phone, encrypt_phone
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(tags=["auth"])


def _user_out(user: User) -> UserOut:
    phone = decrypt_phone(user.phone_encrypted) if user.phone_encrypted else None
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        department=user.department,
        phone=phone,
        rating_avg=user.rating_avg,
        rating_count=user.rating_count,
    )


@router.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.email == body.email))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 가입된 이메일입니다")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        department=body.department,
        phone_encrypted=encrypt_phone(body.phone) if body.phone else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None or db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 refresh 토큰입니다")
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get("/users/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)
