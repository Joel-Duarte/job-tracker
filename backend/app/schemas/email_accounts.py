from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EmailAccountBase(BaseModel):
    name: str = Field(..., examples=["Personal Gmail"], description="Display name for account")
    auth_type: Optional[str] = Field(default="IMAP", description="Auth type: 'IMAP', 'GMAIL_OAUTH', 'MS_GRAPH_OAUTH'")
    username: str = Field(..., examples=["user@gmail.com"], description="Email or login username")
    folder: Optional[str] = Field(default="INBOX", examples=["INBOX"], description="Target mailbox folder")
    imap_host: Optional[str] = Field(default=None, examples=["imap.gmail.com"], description="IMAP server hostname")
    imap_port: Optional[int] = Field(default=993, examples=[993], description="IMAP SSL port")
    is_active: Optional[bool] = Field(default=True, description="Whether account is active for syncs")
    sync_interval: Optional[str] = Field(default="1h", description="Sync schedule interval: 'MANUAL', '15m', '1h', '6h', '24h', 'WEEKLY'")
    sync_schedule_time: Optional[str] = Field(default="09:00", description="24h time format HH:MM for daily/weekly sync")
    sync_schedule_day: Optional[str] = Field(default="MON", description="Day of week: 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'")


class EmailAccountCreate(EmailAccountBase):
    app_password: Optional[str] = Field(default=None, description="App password for basic IMAP auth")
    access_token: Optional[str] = Field(default=None, description="OAuth2 access token")
    refresh_token: Optional[str] = Field(default=None, description="OAuth2 refresh token")
    client_id: Optional[str] = Field(default=None, description="OAuth2 client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth2 client secret")


class EmailAccountUpdate(BaseModel):
    name: Optional[str] = None
    auth_type: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    username: Optional[str] = None
    app_password: Optional[str] = None
    folder: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    sync_cursor: Optional[str] = None
    is_active: Optional[bool] = None
    sync_interval: Optional[str] = None
    sync_schedule_time: Optional[str] = None
    sync_schedule_day: Optional[str] = None


class EmailAccountResponse(EmailAccountBase):
    id: int
    sync_cursor: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)