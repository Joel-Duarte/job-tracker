from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class EmailAccountModel(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Personal Gmail"
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "imap.gmail.com"
    imap_port: Mapped[int] = mapped_column(Integer, default=993, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)  # Email / Login
    app_password: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted/Stored App Password
    folder: Mapped[str] = mapped_column(String(100), default="INBOX", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )