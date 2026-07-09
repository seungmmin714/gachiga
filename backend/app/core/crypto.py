import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    if settings.PHONE_ENC_KEY:
        key = settings.PHONE_ENC_KEY.encode()
    else:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_phone(phone: str) -> str:
    return _fernet().encrypt(phone.encode()).decode()


def decrypt_phone(encrypted: str) -> str | None:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None
