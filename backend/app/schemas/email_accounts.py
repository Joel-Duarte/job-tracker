from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class EmailAccountBase(BaseModel):
    name: str = Field(..., example="Personal Gmail", description="Display name for account")
    imap_host: str = Field(..., example="imap.gmail.com", description="IMAP server hostname")
    imap_port: int = Field(default=993, example=993, description="IMAP SSL port")
    username: str = Field(..., example="user@gmail.com", description="Email or login username")
    folder: str = Field(default="INBOX", example="INBOX", description="Target mailbox folder")
    is_active: bool = Field(default=True, description="Whether account is active for syncs")


class EmailAccountCreate(EmailAccountBase):
    app_password: str = Field(..., example="abcd-efgh-ijkl-mnop", description="App password or secret")


class EmailAccountUpdate(BaseModel):
    name: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    username: Optional[str] = None
    app_password: Optional[str] = None
    folder: Optional[str] = None
    is_active: Optional[bool] = None


class EmailAccountResponse(EmailAccountBase):
    id: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)