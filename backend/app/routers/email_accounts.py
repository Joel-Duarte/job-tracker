import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.email_accounts import EmailAccountModel
from app.schemas.email_accounts import (
    EmailAccountCreate,
    EmailAccountResponse,
    EmailAccountUpdate,
)
from app.services.oauth_adapters import GmailOAuthAdapter, MicrosoftGraphAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email_accounts", tags=["Email Accounts"])


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
        resolved_client_id = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        if resolved_client_id:
            scopes = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={resolved_client_id}&"
                f"redirect_uri={effective_redirect_uri}&"
                f"response_type=code&"
                f"scope={scopes}&"
                f"access_type=offline&"
                f"prompt=consent"
            )
            return OAuthUrlResponse(
                provider="google",
                auth_url=auth_url,
                client_id_configured=True,
                redirect_uri=effective_redirect_uri,
                message="Google OAuth authorization URL generated.",
            )
        return OAuthUrlResponse(
            provider="google",
            auth_url=None,
            client_id_configured=False,
            redirect_uri=effective_redirect_uri,
            message="No Google Client ID configured. You can use App Password for instant connection or enter your Client ID.",
        )

    elif prov in ["microsoft", "outlook"]:
        resolved_client_id = client_id or os.getenv("MS_OAUTH_CLIENT_ID")
        if resolved_client_id:
            scopes = "Mail.Read offline_access User.Read"
            auth_url = (
                f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"client_id={resolved_client_id}&"
                f"response_type=code&"
                f"redirect_uri={effective_redirect_uri}&"
                f"response_mode=query&"
                f"scope={scopes}&"
                f"prompt=consent"
            )
            return OAuthUrlResponse(
                provider="microsoft",
                auth_url=auth_url,
                client_id_configured=True,
                redirect_uri=effective_redirect_uri,
                message="Microsoft Graph OAuth authorization URL generated.",
            )
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
    if error:
        return Response(
            content=f"""
            <html>
                <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                    <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #ef4444;">
                        <h2 style="color: #ef4444; margin-bottom: 8px;">OAuth Authorization Failed</h2>
                        <p style="color: #94a3b8; font-size: 14px;">{error}</p>
                    </div>
                </body>
            </html>
            """,
            media_type="text/html",
        )

    if not code:
        return Response(
            content="<html><body><h3>OAuth Error: No authorization code received.</h3></body></html>",
            media_type="text/html",
        )

    prov = provider.lower().strip()
    base_url = _resolve_base_url(request)
    redirect_uri = f"{base_url}/api/v1/email_accounts/oauth/callback/{prov}"

    try:
        if prov == "google":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or ""
            client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or ""
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

            stmt = select(EmailAccountModel).where(
                EmailAccountModel.username == email_address,
                EmailAccountModel.auth_type == "GMAIL_OAUTH",
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
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
                existing.access_token = access_token
                if refresh_token:
                    existing.refresh_token = refresh_token
                existing.is_active = True

            await db.commit()

        elif prov in ["microsoft", "outlook"]:
            client_id = os.getenv("MS_OAUTH_CLIENT_ID") or ""
            client_secret = os.getenv("MS_OAUTH_CLIENT_SECRET") or ""
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

            stmt = select(EmailAccountModel).where(
                EmailAccountModel.username == email_address,
                EmailAccountModel.auth_type == "MS_GRAPH_OAUTH",
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
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
                existing.access_token = access_token
                if refresh_token:
                    existing.refresh_token = refresh_token
                existing.is_active = True

            await db.commit()

        return Response(
            content="""
            <html>
                <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                    <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #334155;">
                        <h2 style="color: #10b981; margin-bottom: 8px;">✓ Mailbox Connected Successfully!</h2>
                        <p style="color: #94a3b8; font-size: 14px;">Sync authorization established. Closing window...</p>
                        <script>
                            if (window.opener) {
                                window.opener.postMessage({ type: 'oauth_success' }, '*');
                            }
                            setTimeout(() => window.close(), 1200);
                        </script>
                    </div>
                </body>
            </html>
            """,
            media_type="text/html",
        )
    except Exception as err:
        logger.error("OAuth callback exchange failed: %s", err, exc_info=True)
        return Response(
            content=f"""
            <html>
                <body style="font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #f8fafc;">
                    <div style="text-align: center; background: #1e293b; padding: 32px 48px; border-radius: 12px; border: 1px solid #ef4444;">
                        <h2 style="color: #ef4444; margin-bottom: 8px;">OAuth Exchange Failed</h2>
                        <p style="color: #94a3b8; font-size: 14px;">{err!s}</p>
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
        for field, value in update_data.items():
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
