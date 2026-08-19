import base64
import hashlib
import logging

from fastapi import Header, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet():
    from cryptography.fernet import Fernet

    secret_raw = (
        getattr(
            settings,
            "SECRET_KEY",
            "default-development-secret-key-change-in-production",
        )
        or "default-development-secret-key-change-in-production"
    )
    key_bytes = hashlib.sha256(secret_raw.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_secret(plain_text: str | None) -> str | None:
    """Encrypt a sensitive value, preserving already encrypted values."""
    if not plain_text:
        return plain_text

    fernet = _get_fernet()
    try:
        fernet.decrypt(plain_text.encode("utf-8"))
        return plain_text
    except Exception:
        return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Decrypt a value, retaining compatibility with legacy plaintext rows."""
    if not cipher_text:
        return cipher_text

    try:
        return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return cipher_text


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    decrypted = decrypt_secret(secret)
    if not decrypted:
        return None
    if len(decrypted) <= 6:
        return "***"
    if decrypted.startswith("sk-"):
        return f"sk-...{decrypted[-4:]}"
    return f"{decrypted[:3]}...{decrypted[-3:]}"


async def verify_admin_access(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
    authorization: str | None = Header(None),
) -> None:
    expected_secret = getattr(settings, "ADMIN_SECRET", "") or ""
    if not expected_secret:
        return

    provided_token = x_admin_token
    if not provided_token and authorization:
        provided_token = (
            authorization[7:].strip()
            if authorization.lower().startswith("bearer ")
            else authorization.strip()
        )

    if provided_token != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing administrative authorization token.",
        )


async def verify_reset_allowed(
    x_confirm_reset: str | None = Header(None, alias="X-Confirm-Reset"),
    x_admin_confirm: str | None = Header(None, alias="X-Admin-Confirm"),
) -> None:
    env = (getattr(settings, "ENVIRONMENT", "development") or "").strip().lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database reset operations are disabled in production environment.",
        )

    confirmations = {
        (x_confirm_reset or "").strip().lower(),
        (x_admin_confirm or "").strip().lower(),
    }
    if not confirmations.intersection({"true", "1"}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must pass an explicit reset confirmation header.",
        )
