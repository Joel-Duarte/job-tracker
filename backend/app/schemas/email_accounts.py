from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailAccountBase(BaseModel):
    name: str = Field(
        ..., examples=["Personal Gmail"], description="Display name for account"
    )
    auth_type: str | None = Field(
        default="IMAP", description="Auth type: 'IMAP', 'GMAIL_OAUTH', 'MS_GRAPH_OAUTH'"
    )
    username: str = Field(
        ..., examples=["user@gmail.com"], description="Email or login username"
    )
    folder: str | None = Field(
        default="INBOX", examples=["INBOX"], description="Target mailbox folder"
    )
    imap_host: str | None = Field(
        default=None, examples=["imap.gmail.com"], description="IMAP server hostname"
    )
    imap_port: int | None = Field(
        default=993, examples=[993], description="IMAP SSL port"
    )
    is_active: bool | None = Field(
        default=True, description="Whether account is active for syncs"
    )
    sync_interval: str | None = Field(
        default="1h",
        description="Sync schedule interval: 'MANUAL', '15m', '1h', '6h', '24h', 'WEEKLY'",
    )
    sync_schedule_time: str | None = Field(
        default="09:00", description="24h time format HH:MM for daily/weekly sync"
    )
    sync_schedule_day: str | None = Field(
        default="MON",
        description="Day of week: 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'",
    )


class EmailAccountCreate(EmailAccountBase):
    app_password: str | None = Field(
        default=None, description="App password for basic IMAP auth"
    )
    access_token: str | None = Field(default=None, description="OAuth2 access token")
    refresh_token: str | None = Field(default=None, description="OAuth2 refresh token")
    client_id: str | None = Field(default=None, description="OAuth2 client ID")
    client_secret: str | None = Field(default=None, description="OAuth2 client secret")


class EmailAccountUpdate(BaseModel):
    name: str | None = None
    auth_type: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    username: str | None = None
    app_password: str | None = None
    folder: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    sync_cursor: str | None = None
    is_active: bool | None = None
    sync_interval: str | None = None
    sync_schedule_time: str | None = None
    sync_schedule_day: str | None = None


class EmailAccountResponse(EmailAccountBase):
    id: int
    sync_cursor: str | None = None
    last_synced_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
