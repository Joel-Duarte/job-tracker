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
    """Symmetrically encrypts a sensitive plain-text secret using Fernet.

    If the string is already validly encrypted by Fernet, returns it as-is.
    Returns None if input is None or empty.
    """
    if not plain_text:
        return plain_text

    try:
        f = _get_fernet()
        f.decrypt(plain_text.encode("utf-8"))
        # Already encrypted
        return plain_text
    except Exception:
        pass

    f = _get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Decrypts a Fernet ciphertext string into plain-text.

    If decryption fails (e.g., legacy unencrypted string in DB), gracefully returns cipher_text.
    Returns None if input is None.
    """
    if not cipher_text:
        return cipher_text

    try:
        f = _get_fernet()
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return cipher_text


def mask_secret(secret: str | None) -> str | None:
    """Masks secret keys for API responses (e.g., returning sk-...xxxx or sec...xxxx)."""
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
    """Security dependency ensuring administrative authorization if ADMIN_SECRET is configured."""
    expected_secret = getattr(settings, "ADMIN_SECRET", "") or ""
    if not expected_secret:
        # Development mode without explicit admin secret configured
        return

    provided_token = x_admin_token
    if not provided_token and authorization:
        if authorization.lower().startswith("bearer "):
            provided_token = authorization[7:].strip()
        else:
            provided_token = authorization.strip()

    if provided_token != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing administrative authorization token.",
        )


async def verify_reset_allowed(
    x_confirm_reset: str | None = Header(None, alias="X-Confirm-Reset"),
    x_admin_confirm: str | None = Header(None, alias="X-Admin-Confirm"),
) -> None:
    """Security dependency ensuring database reset is allowed and confirmed.

    Blocks database reset in production environment and requires explicit confirmation headers.
    """
    env = (getattr(settings, "ENVIRONMENT", "development") or "").strip().lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database reset operations are disabled in production environment.",
        )

    confirm_reset_val = (x_confirm_reset or "").strip().lower()
    admin_confirm_val = (x_admin_confirm or "").strip().lower()

    if confirm_reset_val not in ("true", "1") and admin_confirm_val not in (
        "true",
        "1",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must pass explicit confirmation header ('X-Confirm-Reset: true' or 'X-Admin-Confirm: true') to execute database reset.",
        )
