from datetime import datetime
from typing import List, Optional
from app.schemas.intake import EmailPayload


async def fetch_emails_from_folder(
    folder_name: str = "INBOX",
    since_date: Optional[datetime] = None,
) -> List[EmailPayload]:
    """Connects to IMAP / Mail provider, fetches emails from `folder_name` 
    filtered after `since_date` (if provided), and maps them into EmailPayload objects.
    """
    emails = []
    
    # 1. Connect to IMAP / Mail server using settings credentials
    # 2. Select folder (e.g. `folder_name`)
    # 3. Apply search criteria (e.g. SINCE since_date if provided)
    # 4. Read body/subject/message_id and append to `emails` list
    
    return emails