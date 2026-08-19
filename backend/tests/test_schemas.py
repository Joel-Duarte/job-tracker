from app.schemas.applications import (
    AllowedApplicationStatus,
    BulkTransitionRequest,
    BulkTransitionResult,
)


def test_new_terminal_statuses_exist():
    assert AllowedApplicationStatus.HIRED == "HIRED"
    assert AllowedApplicationStatus.ARCHIVED == "ARCHIVED"
    assert AllowedApplicationStatus.WITHDRAWN == "WITHDRAWN"


def test_bulk_transition_request_schema():
    req = BulkTransitionRequest(
        target_status=AllowedApplicationStatus.ARCHIVED,
        from_statuses=[
            AllowedApplicationStatus.APPLIED,
            AllowedApplicationStatus.OFFER,
        ],
    )
    assert req.target_status == "ARCHIVED"
    assert "APPLIED" in [str(s) for s in req.from_statuses]
    assert req.exclude_ids == []


def test_bulk_transition_result_schema():
    res = BulkTransitionResult(updated_count=2, updated_ids=[1, 2])
    assert res.updated_count == 2
    assert res.updated_ids == [1, 2]
