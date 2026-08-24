from unittest.mock import MagicMock, patch

import pytest

from app.models.email_accounts import EmailAccountModel
from app.services.email_fetcher import (
    _fetch_imap_emails_sync,
    fetch_emails_from_account,
)


def test_imap_batch_fetching():
    account = EmailAccountModel(
        id=10,
        name="Batch IMAP Test",
        auth_type="IMAP",
        imap_host="imap.example.com",
        imap_port=993,
        username="user@example.com",
        app_password="secret-password",
        folder="INBOX",
    )

    mock_mail = MagicMock()
    mock_mail.search.return_value = ("OK", [b"1 2 3"])

    raw_msg_1 = (
        b"From: sender1@example.com\r\n"
        b"Subject: Test Subject 1\r\n"
        b"Message-ID: <msg-1@example.com>\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"Body content 1"
    )
    raw_msg_2 = (
        b"From: sender2@example.com\r\n"
        b"Subject: Test Subject 2\r\n"
        b"Message-ID: <msg-2@example.com>\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"Body content 2"
    )
    raw_msg_3 = (
        b"From: sender3@example.com\r\n"
        b"Subject: Test Subject 3\r\n"
        b"Message-ID: <msg-3@example.com>\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"Body content 3"
    )

    mock_mail.fetch.return_value = (
        "OK",
        [
            (b"1 (RFC822 {100}", raw_msg_1),
            b")",
            (b"2 (RFC822 {100}", raw_msg_2),
            b")",
            (b"3 (RFC822 {100}", raw_msg_3),
            b")",
        ],
    )

    with patch("imaplib.IMAP4_SSL", return_value=mock_mail):
        emails = _fetch_imap_emails_sync(
            account.imap_host,
            account.imap_port,
            account.username,
            account.app_password,
            account.folder,
            account.id,
        )

        assert len(emails) == 3
        assert emails[0].subject == "Test Subject 1"
        assert emails[1].subject == "Test Subject 2"
        assert emails[2].subject == "Test Subject 3"

        # Verify mail.fetch was called once in a single batch with concatenated sequence "1,2,3"
        mock_mail.fetch.assert_called_once_with(b"1,2,3", "(RFC822)")


@pytest.mark.asyncio
async def test_fetch_emails_from_account_imap_threaded():
    account = EmailAccountModel(
        id=20,
        name="Threaded IMAP Account",
        auth_type="IMAP",
        imap_host="imap.example.com",
        imap_port=993,
        username="user20@example.com",
        app_password="secret-password",
        folder="INBOX",
    )

    with patch(
        "app.services.email_fetcher._fetch_imap_emails_sync", return_value=[]
    ) as mock_sync:
        emails, cursor = await fetch_emails_from_account(account)
        assert emails == []
        assert cursor is None
        mock_sync.assert_called_once_with(
            account.imap_host,
            account.imap_port,
            account.username,
            account.app_password,
            "INBOX",
            account.id,
            None,
            500,
        )
