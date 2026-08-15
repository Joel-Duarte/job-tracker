from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class EmailAccountModel(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Personal Gmail", "Work Outlook"
    auth_type: Mapped[str] = mapped_column(String(50), default="IMAP", nullable=False)  # IMAP, GMAIL_OAUTH, MS_GRAPH_OAUTH

    # IMAP Configuration
    imap_host: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., "imap.gmail.com"
    imap_port: Mapped[int | None] = mapped_column(Integer, default=993, nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)  # Email / Login
    app_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Encrypted/Stored App Password
    folder: Mapped[str] = mapped_column(String(100), default="INBOX", nullable=False)

    # Modern OAuth2 Configuration
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)  # Gmail historyId or MS Graph deltaLink

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_interval: Mapped[str | None] = mapped_column(String(50), default="1h", nullable=True)  # MANUAL, 15m, 1h, 6h, 24h, WEEKLY
    sync_schedule_time: Mapped[str | None] = mapped_column(String(20), default="09:00", nullable=True)  # "09:00" (24h)
    sync_schedule_day: Mapped[str | None] = mapped_column(String(20), default="MON", nullable=True)  # MON, TUE, etc.
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )