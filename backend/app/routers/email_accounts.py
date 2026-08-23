import asyncio
import base64
import binascii
import hashlib
import hmac
import html
import imaplib
import json
import logging
import secrets
import time
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.email_accounts import EmailAccountModel
from app.models.processed_email import ProcessedEmailModel
from app.schemas.email_accounts import (
    EmailAccountCreate,
    EmailAccountResponse,
    EmailAccountUpdate,
)
from app.services.oauth_adapters import GmailOAuthAdapter, MicrosoftGraphAdapter

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/email_accounts",
    tags=["Email Accounts"],
    dependencies=[Depends(verify_admin_access)],
)

_USED_STATES: dict[str, int] = {}
_STATE_COOKIE_NAME = "oauth_state"
_STATE_TTL_SECONDS = 900


def generate_oauth_state(client_id: str | None = None) -> str:
    """Generates a signed cryptographic state token for OAuth CSRF protection."""
    payload = json.dumps(
        {"nonce": secrets.token_urlsafe(16), "client_id": client_id},
        separators=(",", ":"),
    ).encode()
    raw_token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{raw_token}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{raw_token}.{timestamp}.{signature}"


def _oauth_state_client_id(state: str | None) -> str | None:
    if not state:
        return None
    raw_token = state.split(".")[0]
    padding = "=" * (-len(raw_token) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(f"{raw_token}{padding}"))
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError):
        return None
    return payload.get("client_id") if isinstance(payload, dict) else None


def validate_oauth_state(
    state: str | None, expected_raw_token: str | None = None
) -> bool:
    """Validates the OAuth CSRF state token and guards against replay attacks."""
    if not state:
        return False
    parts = state.split(".")
    if len(parts) != 3:
        return False
    raw_token, timestamp_str, signature = parts
    try:
        ts = int(timestamp_str)
    except ValueError:
        return False

    now = int(time.time())
    if now - ts > _STATE_TTL_SECONDS or ts > now + 60:
        return False

    for used_token, expiry in list(_USED_STATES.items()):
        if expiry < now:
            del _USED_STATES[used_token]

    if expected_raw_token is not None and not hmac.compare_digest(
        raw_token, expected_raw_token
    ):
        return False

    expected_sig = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{raw_token}:{timestamp_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return False

    if raw_token in _USED_STATES:
        return False
    _USED_STATES[raw_token] = ts + _STATE_TTL_SECONDS
    return True


def _resolve_base_url(request: Request) -> str:
    """Dynamically resolves the public base URL of the backend.
    Prefers PUBLIC_API_URL if configured in .env (for Docker/reverse proxy),
    otherwise inspects the incoming request headers (host/port/proto).
    """
    if settings.PUBLIC_API_URL:
        return settings.PUBLIC_API_URL.rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or f"{request.url.hostname}:{request.url.port}"
    )
    return f"{forwarded_proto}://{forwarded_host}"


def _resolve_frontend_origin(request: Request) -> str:
    """Resolves the configured frontend origin for OAuth popup messaging."""
    configured_origin = settings.PUBLIC_FRONTEND_URL
    if configured_origin:
        parsed = urlparse(configured_origin)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return _resolve_base_url(request)


def _set_oauth_state_cookie(response: Response, state: str, request: Request) -> None:
    is_secure = (
        request.headers.get("x-forwarded-proto", request.url.scheme).lower() == "https"
    )
    response.set_cookie(
        _STATE_COOKIE_NAME,
        state.split(".", 1)[0],
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
    )


class OAuthUrlResponse(BaseModel):
    provider: str
    auth_url: str | None = None
    client_id_configured: bool
    redirect_uri: str
    message: str


class OAuthConfigResponse(BaseModel):
    base_url: str
    google_redirect_uri: str
    microsoft_redirect_uri: str


@router.get("/oauth/config", response_model=OAuthConfigResponse)
async def get_oauth_config(request: Request):
    """Returns dynamic OAuth configuration including derived redirect URIs for Google and Microsoft."""
    base_url = _resolve_base_url(request)
    return OAuthConfigResponse(
        base_url=base_url,
        google_redirect_uri=f"{base_url}/api/v1/email_accounts/oauth/callback/google",
        microsoft_redirect_uri=f"{base_url}/api/v1/email_accounts/oauth/callback/microsoft",
    )


@router.get("/oauth/authorize-url", response_model=OAuthUrlResponse)
async def get_oauth_authorize_url(
    request: Request,
    provider: str = Query(..., description="Provider: 'google' or 'microsoft'"),
    client_id: str | None = Query(None, description="Custom OAuth Client ID"),
    redirect_uri: str | None = Query(
        None,
        description="Redirect URI (optional, auto-derived from host / PUBLIC_API_URL)",
    ),
):
    """Returns OAuth2 authorization URL for Google Gmail or Microsoft 365."""
    prov = provider.lower().strip()
    base_url = _resolve_base_url(request)

    # Auto-resolve redirect URI if not explicitly passed
    effective_redirect_uri = (
        redirect_uri or f"{base_url}/api/v1/email_accounts/oauth/callback/{prov}"
    )

    if prov == "google":
        resolved_client_id = client_id
        if resolved_client_id:
            state_token = generate_oauth_state(resolved_client_id)
            query_params = {
                "client_id": resolved_client_id,
                "redirect_uri": effective_redirect_uri,
                "response_type": "code",
                "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email openid profile",
                "access_type": "offline",
                "prompt": "consent",
                "state": state_token,
            }
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(query_params)}"
            response = JSONResponse(
                content=OAuthUrlResponse(
                    provider="google",
                    auth_url=auth_url,
                    client_id_configured=True,
                    redirect_uri=effective_redirect_uri,
                    message="Google OAuth authorization URL generated.",
                ).model_dump()
            )
            _set_oauth_state_cookie(response, state_token, request)
            return response
        return OAuthUrlResponse(
            provider="google",
            auth_url=None,
            client_id_configured=False,
            redirect_uri=effective_redirect_uri,
            message="No Google Client ID configured. You can use App Password for instant connection or enter your Client ID.",
        )

    elif prov in ["microsoft", "outlook"]:
        resolved_client_id = client_id
        if resolved_client_id:
            state_token = generate_oauth_state(resolved_client_id)
            scopes = "openid email profile User.Read Mail.Read offline_access"
            auth_url = (
                f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
                f"client_id={resolved_client_id}&"
                f"response_type=code&"
                f"redirect_uri={effective_redirect_uri}&"
                f"response_mode=query&"
                f"scope={scopes}&"
                f"prompt=consent&"
                f"state={state_token}"
            )
            response = JSONResponse(
                content=OAuthUrlResponse(
                    provider="microsoft",
                    auth_url=auth_url,
                    client_id_configured=True,
                    redirect_uri=effective_redirect_uri,
                    message="Microsoft Graph OAuth authorization URL generated.",
                ).model_dump()
            )
            _set_oauth_state_cookie(response, state_token, request)
            return response
        return OAuthUrlResponse(
            provider="microsoft",
            auth_url=None,
            client_id_configured=False,
            redirect_uri=effective_redirect_uri,
            message="No Microsoft Client ID configured. You can use App Password or IMAP for instant connection.",
        )

    raise HTTPException(
        status_code=400, detail=f"Unsupported OAuth provider: {provider}"
    )


@router.get("/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = Query(None),
    error: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handles OAuth authorization redirect callback from Google Gmail or Microsoft Graph."""
    try:
        state_cookie = request.cookies.get(_STATE_COOKIE_NAME)
        if not validate_oauth_state(state, state_cookie):
            return Response(
                content="""
                <html><body><h3>OAuth Authorization Failed: Invalid or expired CSRF state.</h3></body></html>
                """,
                media_type="text/html",
                status_code=400,
            )

        if error:
            response = Response(
                content=f"""
                <html>
                    <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                        <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #ef4444;">
                            <h2 style="color: #ef4444; margin-bottom: 8px;">OAuth Authorization Failed</h2>
                            <p style="color: #94a3b8; font-size: 14px;">{html.escape(error)}</p>
                        </div>
                    </body>
                </html>
                """,
                media_type="text/html",
                status_code=400,
            )
            response.delete_cookie(_STATE_COOKIE_NAME, path="/")
            return response

        if not code:
            return Response(
                content="<html><body><h3>OAuth Error: No authorization code received.</h3></body></html>",
                media_type="text/html",
                status_code=400,
            )

        prov = provider.lower().strip()
        state_client_id = _oauth_state_client_id(state)
        auth_type = "GMAIL_OAUTH" if prov == "google" else "MS_GRAPH_OAUTH"
        configured_account = None
        if state_client_id:
            configured_stmt = (
                select(EmailAccountModel)
                .where(
                    EmailAccountModel.client_id == state_client_id,
                    EmailAccountModel.auth_type == auth_type,
                )
                .order_by(EmailAccountModel.id.desc())
            )
            configured_account = (await db.execute(configured_stmt)).scalars().first()

        base_url = _resolve_base_url(request)
        redirect_uri = f"{base_url}/api/v1/email_accounts/oauth/callback/{prov}"

        if prov == "google":
            client_id = state_client_id or ""
            client_secret = (
                configured_account.client_secret if configured_account else ""
            )
            tokens = await GmailOAuthAdapter.exchange_code_for_tokens(
                client_id=client_id,
                client_secret=client_secret,
                code=code,
                redirect_uri=redirect_uri,
            )
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            # Fetch user email profile from Google
            async with httpx.AsyncClient(timeout=10.0) as client:
                p_resp = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                p_data = p_resp.json() if p_resp.status_code == 200 else {}
                email_address = p_data.get("emailAddress", "Google Account")

            stmt = (
                select(EmailAccountModel)
                .where(
                    EmailAccountModel.username == email_address,
                    EmailAccountModel.auth_type == "GMAIL_OAUTH",
                )
                .order_by(EmailAccountModel.id.desc())
            )
            existing = (await db.execute(stmt)).scalars().first()
            existing = existing or configured_account
            if not existing:
                account = EmailAccountModel(
                    name=f"Gmail ({email_address})",
                    auth_type="GMAIL_OAUTH",
                    username=email_address,
                    folder="INBOX",
                    access_token=access_token,
                    refresh_token=refresh_token,
                    client_id=client_id or None,
                    client_secret=client_secret or None,
                    is_active=True,
                )
                db.add(account)
            else:
                existing.username = email_address
                existing.name = existing.name or f"Gmail ({email_address})"
                existing.access_token = access_token
                if refresh_token:
                    existing.refresh_token = refresh_token
                existing.is_active = True

            await db.commit()

        elif prov in ["microsoft", "outlook"]:
            client_id = state_client_id or ""
            client_secret = (
                configured_account.client_secret if configured_account else ""
            )
            tokens = await MicrosoftGraphAdapter.exchange_code_for_tokens(
                client_id=client_id,
                client_secret=client_secret,
                code=code,
                redirect_uri=redirect_uri,
            )
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            # Fetch user email profile from MS Graph
            async with httpx.AsyncClient(timeout=10.0) as client:
                p_resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                p_data = p_resp.json() if p_resp.status_code == 200 else {}
                email_address = (
                    p_data.get("mail")
                    or p_data.get("userPrincipalName")
                    or "Outlook Account"
                )

            stmt = (
                select(EmailAccountModel)
                .where(
                    EmailAccountModel.username == email_address,
                    EmailAccountModel.auth_type == "MS_GRAPH_OAUTH",
                )
                .order_by(EmailAccountModel.id.desc())
            )
            existing = (await db.execute(stmt)).scalars().first()
            existing = existing or configured_account
            if not existing:
                account = EmailAccountModel(
                    name=f"Outlook ({email_address})",
                    auth_type="MS_GRAPH_OAUTH",
                    username=email_address,
                    folder="INBOX",
                    access_token=access_token,
                    refresh_token=refresh_token,
                    client_id=client_id or None,
                    client_secret=client_secret or None,
                    is_active=True,
                )
                db.add(account)
            else:
                existing.username = email_address
                existing.name = existing.name or f"Outlook ({email_address})"
                existing.access_token = access_token
                if refresh_token:
                    existing.refresh_token = refresh_token
                existing.is_active = True

            await db.commit()

        frontend_origin = _resolve_frontend_origin(request)
        response = Response(
            content=f"""
            <html>
                <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                    <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #334155;">
                        <h2 style="color: #10b981; margin-bottom: 8px;">✓ Mailbox Connected Successfully!</h2>
                        <p style="color: #94a3b8; font-size: 14px;">Sync authorization established. Closing window...</p>
                        <script>
                            const payload = {{ type: 'oauth_success', provider: {json.dumps(prov)}, timestamp: Date.now() }};

                            // 1. PostMessage to opener window (if opener exists and is reachable)
                            if (window.opener) {{
                                try {{
                                    window.opener.postMessage(payload, {json.dumps(frontend_origin)});
                                }} catch (e) {{
                                    console.warn('postMessage failed:', e);
                                }}
                            }}

                            // 2. BroadcastChannel across all open tabs/windows on same origin
                            try {{
                                const bc = new BroadcastChannel('jobtracker_oauth_channel');
                                bc.postMessage(payload);
                                bc.close();
                            }} catch (e) {{
                                console.warn('BroadcastChannel failed:', e);
                            }}

                            // 3. LocalStorage event for cross-window fallback
                            try {{
                                localStorage.setItem('jobtracker_oauth_success', JSON.stringify(payload));
                            }} catch (e) {{
                                console.warn('localStorage setItem failed:', e);
                            }}

                            setTimeout(() => {{
                                window.close();
                            }}, 1200);
                        </script>
                    </div>
                </body>
            </html>
            """,
            media_type="text/html",
        )
        response.delete_cookie(_STATE_COOKIE_NAME, path="/")
        return response
    except Exception as err:
        logger.error("OAuth callback exchange failed: %s", err, exc_info=True)
        return Response(
            content=f"""
            <html>
                <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                    <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #ef4444;">
                        <h2 style="color: #ef4444; margin-bottom: 8px;">OAuth Exchange Failed</h2>
                        <p style="color: #94a3b8; font-size: 14px;">{html.escape(str(err))}</p>
                    </div>
                </body>
            </html>
            """,
            media_type="text/html",
        )


@router.get("", response_model=list[EmailAccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """List all configured email provider accounts."""
    try:
        result = await db.execute(
            select(EmailAccountModel).order_by(EmailAccountModel.id)
        )
        accounts = result.scalars().all()
        for acc in accounts:
            if not getattr(acc, "sync_interval", None):
                acc.sync_interval = "1h"
            if not getattr(acc, "sync_schedule_time", None):
                acc.sync_schedule_time = "09:00"
            if not getattr(acc, "sync_schedule_day", None):
                acc.sync_schedule_day = "MON"
        return accounts
    except Exception as e:
        logger.error(f"Error listing email accounts: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list email accounts: {e!s}",
        )


@router.get("/{account_id}", response_model=EmailAccountResponse)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch details of a specific email account by ID."""
    result = await db.execute(
        select(EmailAccountModel).where(EmailAccountModel.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {account_id} not found.",
        )
    if not getattr(account, "sync_interval", None):
        account.sync_interval = "1h"
    if not getattr(account, "sync_schedule_time", None):
        account.sync_schedule_time = "09:00"
    if not getattr(account, "sync_schedule_day", None):
        account.sync_schedule_day = "MON"
    return account


@router.post(
    "", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_account(
    payload: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new email account configuration."""
    try:
        data = payload.model_dump()
        account = EmailAccountModel(**data)
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating email account: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create email account: {e!s}",
        )


@router.patch("/{account_id}", response_model=EmailAccountResponse)
async def update_account(
    account_id: int,
    payload: EmailAccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update settings or credentials for an existing email account."""
    result = await db.execute(
        select(EmailAccountModel).where(EmailAccountModel.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {account_id} not found.",
        )

    try:
        update_data = payload.model_dump(exclude_unset=True)
        masked_fields = {
            "app_password",
            "access_token",
            "refresh_token",
            "client_secret",
        }
        for field, value in update_data.items():
            if field in masked_fields and (value == "********" or value is None):
                continue
            setattr(account, field, value)

        await db.commit()
        await db.refresh(account)
        return account
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating email account {account_id}: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update email account: {e!s}",
        )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Remove an email account configuration."""
    result = await db.execute(
        select(EmailAccountModel).where(EmailAccountModel.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {account_id} not found.",
        )

    await db.delete(account)
    await db.commit()


class MailFolderItem(BaseModel):
    id: str
    name: str
    path: str
    parent_id: str | None = None


class EmailFoldersResponse(BaseModel):
    account_id: int
    folders: list[MailFolderItem]


async def fetch_account_folders(
    account: EmailAccountModel, db: AsyncSession | None = None
) -> list[MailFolderItem]:
    """Fetches list of available mail folders / labels from IMAP, Gmail API, or Microsoft Graph."""
    logger.info(
        "Fetching mail folders for account ID %s (auth_type=%s, username=%s)",
        account.id,
        account.auth_type,
        account.username,
    )
    if account.auth_type == "GMAIL_OAUTH":
        if not account.access_token:
            return [MailFolderItem(id="INBOX", name="Inbox", path="Inbox")]
        try:
            access_token = account.access_token
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if (
                    resp.status_code == 401
                    and account.refresh_token
                    and account.client_id
                    and account.client_secret
                ):
                    access_token = await GmailOAuthAdapter.refresh_access_token(
                        client_id=account.client_id,
                        client_secret=account.client_secret,
                        refresh_token=account.refresh_token,
                    )
                    account.access_token = access_token
                    if db:
                        await db.commit()
                    resp = await client.get(
                        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    labels_raw = data.get("labels", [])
                    ignored_ids = {
                        "CHAT",
                        "DRAFT",
                        "TRASH",
                        "SPAM",
                        "UNREAD",
                        "CATEGORY_FORUMS",
                        "CATEGORY_UPDATES",
                        "CATEGORY_PROMOTIONS",
                        "CATEGORY_SOCIAL",
                    }
                    items: list[MailFolderItem] = []
                    for item in labels_raw:
                        lbl_id = item.get("id")
                        lbl_name = item.get("name")
                        if not lbl_id or not lbl_name:
                            continue
                        if lbl_id.upper() in ignored_ids:
                            continue

                        # Friendly naming and path reconstruction
                        if lbl_id.upper() == "INBOX":
                            display_name = "Inbox"
                            path = "Inbox"
                        elif lbl_id.upper() == "SENT":
                            display_name = "Sent"
                            path = "Sent"
                        elif lbl_id.upper() == "STARRED":
                            display_name = "Starred"
                            path = "Starred"
                        elif lbl_id.upper() == "IMPORTANT":
                            display_name = "Important"
                            path = "Important"
                        elif lbl_id.upper() == "CATEGORY_PERSONAL":
                            display_name = "Primary"
                            path = "Primary"
                        else:
                            # User label (can be nested like Projects/Jobs)
                            display_name = (
                                lbl_name.split("/")[-1] if "/" in lbl_name else lbl_name
                            )
                            path = lbl_name.replace("/", " / ")

                        items.append(
                            MailFolderItem(
                                id=lbl_id,
                                name=display_name,
                                path=path,
                            )
                        )

                    items.sort(
                        key=lambda x: (
                            0 if x.id.upper() == "INBOX" else 1,
                            x.path.lower(),
                        )
                    )
                    return (
                        items
                        if items
                        else [MailFolderItem(id="INBOX", name="Inbox", path="Inbox")]
                    )
                else:
                    logger.warning(
                        "Gmail API labels error: status=%s body=%s",
                        resp.status_code,
                        resp.text,
                    )
        except Exception as e:
            logger.warning("Error fetching Gmail labels: %s", e, exc_info=True)
        return [
            MailFolderItem(id="INBOX", name="Inbox", path="Inbox"),
            MailFolderItem(id="Archive", name="Archive", path="Archive"),
            MailFolderItem(id="Jobs", name="Jobs", path="Jobs"),
        ]

    elif account.auth_type == "MS_GRAPH_OAUTH":
        if not account.access_token:
            return [MailFolderItem(id="Inbox", name="Inbox", path="Inbox")]
        try:
            access_token = account.access_token
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = "https://graph.microsoft.com/v1.0/me/mailFolders/delta"
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if (
                    resp.status_code == 401
                    and account.refresh_token
                    and account.client_id
                    and account.client_secret
                ):
                    access_token = await MicrosoftGraphAdapter.refresh_access_token(
                        client_id=account.client_id,
                        client_secret=account.client_secret,
                        refresh_token=account.refresh_token,
                    )
                    account.access_token = access_token
                    if db:
                        await db.commit()
                    resp = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )

                raw_folders: dict[str, dict] = {}
                while resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("value", []):
                        f_id = item.get("id")
                        f_name = item.get("displayName")
                        parent_id = item.get("parentFolderId")
                        if f_id and f_name:
                            raw_folders[f_id] = {
                                "id": f_id,
                                "name": f_name,
                                "parent_id": parent_id,
                            }
                    next_url = data.get("@odata.nextLink")
                    if not next_url:
                        break
                    resp = await client.get(
                        next_url,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )

                if raw_folders:

                    def build_path(folder_id: str, visited: set | None = None) -> str:
                        if visited is None:
                            visited = set()
                        if folder_id in visited or folder_id not in raw_folders:
                            return ""
                        visited.add(folder_id)
                        f = raw_folders[folder_id]
                        parent_id = f.get("parent_id")
                        if parent_id and parent_id in raw_folders:
                            parent_name = raw_folders[parent_id]["name"].lower()
                            if parent_name not in {
                                "msgfolderroot",
                                "root",
                                "top of information store",
                            }:
                                parent_path = build_path(parent_id, visited)
                                if parent_path:
                                    return f"{parent_path} / {f['name']}"
                        return f["name"]

                    ignored = {
                        "msgfolderroot",
                        "top of information store",
                        "root",
                        "junk email",
                        "deleted items",
                        "outbox",
                        "conversation history",
                        "sync issues",
                        "conflicts",
                        "local failures",
                        "server failures",
                    }
                    items: list[MailFolderItem] = []
                    for f_id, f in raw_folders.items():
                        if f["name"].lower() in ignored:
                            continue
                        full_path = build_path(f_id)
                        items.append(
                            MailFolderItem(
                                id=f_id,
                                name=f["name"],
                                path=full_path or f["name"],
                                parent_id=f.get("parent_id"),
                            )
                        )

                    items.sort(
                        key=lambda x: (
                            0 if x.name.lower() == "inbox" and "/" not in x.path else 1,
                            x.path.lower(),
                        )
                    )
                    return (
                        items
                        if items
                        else [MailFolderItem(id="Inbox", name="Inbox", path="Inbox")]
                    )
                else:
                    logger.warning(
                        "MS Graph mailFolders/delta returned no folders (status=%s body=%s)",
                        resp.status_code,
                        resp.text,
                    )
        except Exception as e:
            logger.warning(
                "Error fetching MS Graph delta folders: %s", e, exc_info=True
            )
        return [
            MailFolderItem(id="Inbox", name="Inbox", path="Inbox"),
            MailFolderItem(id="Archive", name="Archive", path="Archive"),
            MailFolderItem(id="Jobs", name="Jobs", path="Jobs"),
        ]

    else:
        # Standard IMAP
        if not account.imap_host or not account.username or not account.app_password:
            return [MailFolderItem(id="INBOX", name="INBOX", path="INBOX")]
        try:

            def _get_imap_folders():
                mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port or 993)
                mail.login(account.username, account.app_password)
                status, folder_list = mail.list()
                mail.logout()
                if status != "OK" or not folder_list:
                    return [MailFolderItem(id="INBOX", name="INBOX", path="INBOX")]
                parsed = []
                for entry in folder_list:
                    if isinstance(entry, bytes):
                        entry = entry.decode("utf-8", errors="ignore")
                    parts = entry.split(' "/" ')
                    if len(parts) > 1:
                        raw_folder = parts[-1].strip().strip('"')
                        if raw_folder:
                            parsed.append(raw_folder)
                    else:
                        tokens = entry.split()
                        if tokens:
                            parsed.append(tokens[-1].strip('"'))
                items = [
                    MailFolderItem(
                        id=f,
                        name=f.split("/")[-1] if "/" in f else f,
                        path=f.replace("/", " / "),
                    )
                    for f in sorted(list(set(parsed)))
                ]
                items.sort(
                    key=lambda x: (
                        0 if x.name.upper() == "INBOX" else 1,
                        x.path.lower(),
                    )
                )
                return (
                    items
                    if items
                    else [MailFolderItem(id="INBOX", name="INBOX", path="INBOX")]
                )

            return await asyncio.to_thread(_get_imap_folders)
        except Exception as e:
            logger.warning("Error fetching IMAP folders: %s", e, exc_info=True)
            return [MailFolderItem(id="INBOX", name="INBOX", path="INBOX")]


@router.get("/{account_id}/folders", response_model=EmailFoldersResponse)
async def list_account_folders(account_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch available mail folders/labels from provider for account."""
    result = await db.execute(
        select(EmailAccountModel).where(EmailAccountModel.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {account_id} not found.",
        )

    folders = await fetch_account_folders(account, db=db)
    return EmailFoldersResponse(account_id=account.id, folders=folders)


@router.delete("/processed-emails/all", status_code=status.HTTP_200_OK)
async def clear_all_processed_emails(db: AsyncSession = Depends(get_db)):
    """Deletes all email deduplication history records across all accounts and resets sync cursors."""
    del_result = await db.execute(delete(ProcessedEmailModel))
    deleted_count = del_result.rowcount or 0

    acc_res = await db.execute(select(EmailAccountModel))
    accounts = acc_res.scalars().all()
    for acc in accounts:
        acc.sync_cursor = None
        acc.last_synced_at = None

    await db.commit()

    logger.info(
        "Cleared all %d processed email records across %d accounts.",
        deleted_count,
        len(accounts),
    )
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Cleared {deleted_count} email sync history record(s) across all accounts.",
    }


@router.delete("/{account_id}/processed-emails", status_code=status.HTTP_200_OK)
async def clear_account_processed_emails(
    account_id: int, db: AsyncSession = Depends(get_db)
):
    """Deletes all email deduplication history records for a specific account and resets its sync cursor."""
    result = await db.execute(
        select(EmailAccountModel).where(EmailAccountModel.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {account_id} not found.",
        )

    del_result = await db.execute(
        delete(ProcessedEmailModel).where(ProcessedEmailModel.account_id == account_id)
    )
    deleted_count = del_result.rowcount or 0

    account.sync_cursor = None
    account.last_synced_at = None
    await db.commit()

    account_name = account.name or account.username or f"Account #{account_id}"
    logger.info(
        "Cleared %d processed email records for account %s (ID %d).",
        deleted_count,
        account_name,
        account_id,
    )
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Cleared {deleted_count} email sync history record(s) for {account_name}.",
    }
