from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.staging import StagingItemModel
from app.routers.staging import clear_resolved_staging_items, list_staging_items


@pytest.mark.asyncio
async def test_staging_search_and_pagination(db_session):
    """Test searching and paginating staging items."""
    # Seed 3 items with distinct companies / positions / senders
    item1 = StagingItemModel(
        email_sender="recruiter@stripe.com",
        email_sender_name="Stripe Talent",
        email_subject="Stripe: Software Engineer Interview",
        extracted_data={"company": "Stripe", "position": "Software Engineer"},
        match_reason="LOW_FUZZY_MATCH_CONFIDENCE",
        status="PENDING",
    )
    item2 = StagingItemModel(
        email_sender="jobs@figma.com",
        email_sender_name="Figma Careers",
        email_subject="Figma: Frontend Specialist Application",
        extracted_data={"company": "Figma", "position": "Frontend Specialist"},
        match_reason="AMBIGUOUS_POSITION",
        status="PENDING",
    )
    item3 = StagingItemModel(
        email_sender="hiring@datadog.com",
        email_sender_name="Datadog Recruiting",
        email_subject="Datadog Application Update",
        extracted_data={"company": "Datadog", "position": "Site Reliability Engineer"},
        match_reason="LOW_FUZZY_MATCH_CONFIDENCE",
        status="PROCESSED",
    )
    db_session.add_all([item1, item2, item3])
    await db_session.commit()

    # 1. Test listing pending items with pagination limit 1
    res = await list_staging_items(
        status_filter="PENDING", limit=1, offset=0, db=db_session
    )
    assert res.total == 2
    assert len(res.items) == 1

    # 2. Test search for "Figma"
    res_search = await list_staging_items(
        status_filter="PENDING", search="Figma", limit=10, offset=0, db=db_session
    )
    assert res_search.total == 1
    assert len(res_search.items) == 1
    assert res_search.items[0].email_sender == "jobs@figma.com"

    # 3. Test search for sender email "stripe.com"
    res_sender = await list_staging_items(
        status_filter="PENDING", search="stripe.com", limit=10, offset=0, db=db_session
    )
    assert res_sender.total == 1
    assert res_sender.items[0].email_subject == "Stripe: Software Engineer Interview"


@pytest.mark.asyncio
async def test_clear_resolved_staging_items(db_session):
    """Test clearing PROCESSED staging items with and without days_older_than cutoff."""
    now = datetime.now(UTC)

    # Item 1: PROCESSED created 15 days ago
    item_old = StagingItemModel(
        email_sender="old@company.com",
        email_subject="Old Processed Lead",
        extracted_data={"company": "OldCo"},
        status="PROCESSED",
        created_at=now - timedelta(days=15),
    )
    # Item 2: PROCESSED created 2 days ago
    item_recent = StagingItemModel(
        email_sender="recent@company.com",
        email_subject="Recent Processed Lead",
        extracted_data={"company": "RecentCo"},
        status="PROCESSED",
        created_at=now - timedelta(days=2),
    )
    # Item 3: PENDING item (must NEVER be deleted)
    item_pending = StagingItemModel(
        email_sender="pending@company.com",
        email_subject="Pending Action Required",
        extracted_data={"company": "PendingCo"},
        status="PENDING",
        created_at=now - timedelta(days=20),
    )
    db_session.add_all([item_old, item_recent, item_pending])
    await db_session.commit()

    # 1. Purge items older than 7 days -> should only delete item_old
    res_7d = await clear_resolved_staging_items(days_older_than=7, db=db_session)
    assert res_7d["deleted_count"] == 1

    # Verify item_recent and item_pending still exist
    all_items = (await db_session.execute(select(StagingItemModel))).scalars().all()
    statuses = {item.email_subject: item.status for item in all_items}
    assert "Old Processed Lead" not in statuses
    assert statuses["Recent Processed Lead"] == "PROCESSED"
    assert statuses["Pending Action Required"] == "PENDING"

    # 2. Purge all remaining resolved items (days_older_than=None) -> deletes item_recent
    res_all = await clear_resolved_staging_items(days_older_than=None, db=db_session)
    assert res_all["deleted_count"] == 1

    # Verify pending item is STILL preserved
    remaining = (await db_session.execute(select(StagingItemModel))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].email_subject == "Pending Action Required"
    assert remaining[0].status == "PENDING"


@pytest.mark.asyncio
async def test_staging_server_side_sorting(db_session):
    """Test server-side sorting by received_at ASC (FIFO) and DESC (LIFO)."""
    now = datetime.now(UTC)

    item1 = StagingItemModel(
        email_sender="recruiter1@company.com",
        email_subject="First Email (Oldest)",
        extracted_data={"company": "Company 1"},
        status="PENDING",
        email_received_at=now - timedelta(days=10),
    )
    item2 = StagingItemModel(
        email_sender="recruiter2@company.com",
        email_subject="Second Email (Middle)",
        extracted_data={"company": "Company 2"},
        status="PENDING",
        email_received_at=now - timedelta(days=5),
    )
    item3 = StagingItemModel(
        email_sender="recruiter3@company.com",
        email_subject="Third Email (Newest)",
        extracted_data={"company": "Company 3"},
        status="PENDING",
        email_received_at=now - timedelta(days=1),
    )
    db_session.add_all([item1, item2, item3])
    await db_session.commit()

    # 1. Test FIFO (Oldest First / ASC)
    res_fifo = await list_staging_items(
        status_filter="PENDING",
        sort_by="received_at",
        sort_order="asc",
        limit=2,
        offset=0,
        db=db_session,
    )
    assert res_fifo.total == 3
    assert len(res_fifo.items) == 2
    assert res_fifo.items[0].email_subject == "First Email (Oldest)"
    assert res_fifo.items[1].email_subject == "Second Email (Middle)"

    # 2. Test LIFO (Newest First / DESC)
    res_lifo = await list_staging_items(
        status_filter="PENDING",
        sort_by="received_at",
        sort_order="desc",
        limit=2,
        offset=0,
        db=db_session,
    )
    assert res_lifo.total == 3
    assert len(res_lifo.items) == 2
    assert res_lifo.items[0].email_subject == "Third Email (Newest)"
    assert res_lifo.items[1].email_subject == "Second Email (Middle)"


@pytest.mark.asyncio
async def test_staging_bulk_dismiss(db_session):
    """Test bulk dismissing specific item IDs and all pending items."""
    from app.routers.staging import bulk_dismiss_staging_items
    from app.schemas.staging import StagingBulkDismissRequest

    item1 = StagingItemModel(
        email_sender="user1@company.com",
        email_subject="Dismiss Item 1",
        extracted_data={"company": "C1"},
        status="PENDING",
    )
    item2 = StagingItemModel(
        email_sender="user2@company.com",
        email_subject="Dismiss Item 2",
        extracted_data={"company": "C2"},
        status="PENDING",
    )
    item3 = StagingItemModel(
        email_sender="user3@company.com",
        email_subject="Keep Item 3",
        extracted_data={"company": "C3"},
        status="PENDING",
    )
    db_session.add_all([item1, item2, item3])
    await db_session.commit()
    await db_session.refresh(item1)
    await db_session.refresh(item2)
    await db_session.refresh(item3)

    # 1. Bulk dismiss item1 and item2
    req = StagingBulkDismissRequest(item_ids=[item1.id, item2.id])
    res = await bulk_dismiss_staging_items(req, db=db_session)
    assert res.dismissed_count == 2

    # Verify only item3 remains
    remaining = (await db_session.execute(select(StagingItemModel))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == item3.id

    # 2. Bulk dismiss all pending
    req_all = StagingBulkDismissRequest(
        dismiss_all_pending=True, status_filter="PENDING"
    )
    res_all = await bulk_dismiss_staging_items(req_all, db=db_session)
    assert res_all.dismissed_count == 1

    remaining_after = (
        (await db_session.execute(select(StagingItemModel))).scalars().all()
    )
    assert len(remaining_after) == 0
