"""API endpoints for ATI Requests."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.ati_request import RequestStatus, RequestOutcome
from src.repositories.ati_request import ATIRequestRepository
from src.repositories.public_body import PublicBodyRepository
from src.schemas.ati_request import (
    ATIRequestCreate,
    ATIRequestUpdate,
    ATIRequestResponse,
    ATIRequestListResponse,
)

router = APIRouter()


def _enrich_response(request) -> ATIRequestResponse:
    """Enrich ATI request response with computed fields."""
    response = ATIRequestResponse.model_validate(request)
    
    # Calculate response_days if completed
    if request.completion_date and request.submission_date:
        response.response_days = (request.completion_date - request.submission_date).days
    
    # Check if overdue
    if request.status not in [RequestStatus.COMPLETED, RequestStatus.ABANDONED]:
        response.is_overdue = request.due_date < date.today()
    
    return response


@router.get("", response_model=ATIRequestListResponse)
async def list_ati_requests(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    public_body_id: Optional[UUID] = Query(None, description="Filter by public body"),
    status_filter: Optional[RequestStatus] = Query(None, alias="status", description="Filter by status"),
    outcome_filter: Optional[RequestOutcome] = Query(None, alias="outcome", description="Filter by outcome"),
    start_date: Optional[date] = Query(None, description="Filter by submission date (start)"),
    end_date: Optional[date] = Query(None, description="Filter by submission date (end)"),
    overdue_only: bool = Query(False, description="Only return overdue requests"),
    db: AsyncSession = Depends(get_db),
) -> ATIRequestListResponse:
    """List ATI requests with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **public_body_id**: Filter by specific public body
    - **status**: Filter by request status
    - **outcome**: Filter by request outcome
    - **start_date**: Filter submissions on or after this date
    - **end_date**: Filter submissions on or before this date
    - **overdue_only**: Only return requests past their due date
    """
    repo = ATIRequestRepository(db)
    skip = (page - 1) * page_size
    
    # Handle special cases
    if overdue_only:
        items = await repo.get_overdue(skip=skip, limit=page_size)
        total = len(items)  # Simplified for overdue
    elif public_body_id:
        items = await repo.get_by_public_body(
            public_body_id,
            skip=skip,
            limit=page_size,
            status=status_filter
        )
        total = await repo.count()  # Would need filtered count in production
    elif start_date and end_date:
        items = await repo.get_by_date_range(
            start_date,
            end_date,
            skip=skip,
            limit=page_size
        )
        total = len(items)  # Simplified
    else:
        items = await repo.get_many(skip=skip, limit=page_size)
        total = await repo.count()
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return ATIRequestListResponse(
        items=[_enrich_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=ATIRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_ati_request(
    data: ATIRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> ATIRequestResponse:
    """Create a new ATI request.
    
    - **request_number**: Public reference number (required, must be unique)
    - **public_body_id**: ID of the handling public body (required)
    - **submission_date**: Date the request was received (required)
    - **request_type**: Type of request (default: non_personal)
    - **due_date**: Statutory deadline for response (required)
    - **summary**: Brief description of the request (optional)
    """
    repo = ATIRequestRepository(db)
    public_body_repo = PublicBodyRepository(db)
    
    # Verify public body exists
    public_body = await public_body_repo.get_by_id(data.public_body_id)
    if not public_body:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public body with ID '{data.public_body_id}' not found",
        )
    
    # Check if request number already exists
    existing = await repo.get_by_request_number(data.request_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ATI request with number '{data.request_number}' already exists",
        )
    
    ati_request = await repo.create(data.model_dump())
    return _enrich_response(ati_request)


@router.get("/overdue", response_model=ATIRequestListResponse)
async def list_overdue_requests(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> ATIRequestListResponse:
    """List all overdue ATI requests.
    
    Returns requests that are past their due date and not yet completed or abandoned.
    """
    repo = ATIRequestRepository(db)
    skip = (page - 1) * page_size
    
    items = await repo.get_overdue(skip=skip, limit=page_size)
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return ATIRequestListResponse(
        items=[_enrich_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/statistics")
async def get_statistics(
    public_body_id: Optional[UUID] = Query(None, description="Filter by public body"),
    start_date: Optional[date] = Query(None, description="Start date for stats"),
    end_date: Optional[date] = Query(None, description="End date for stats"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get ATI request statistics.
    
    Returns aggregated statistics including:
    - Count by status
    - Count by outcome
    - Average response time
    """
    repo = ATIRequestRepository(db)
    
    status_counts = await repo.count_by_status(public_body_id)
    outcome_counts = await repo.count_by_outcome(public_body_id)
    avg_response_time = await repo.calculate_average_response_time(
        public_body_id, start_date, end_date
    )
    
    return {
        "by_status": {str(k.value): v for k, v in status_counts.items()},
        "by_outcome": {str(k.value): v for k, v in outcome_counts.items()},
        "average_response_days": round(avg_response_time, 1) if avg_response_time else None,
        "total_requests": sum(status_counts.values()),
    }


@router.get("/{request_id}", response_model=ATIRequestResponse)
async def get_ati_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ATIRequestResponse:
    """Get a specific ATI request by ID."""
    repo = ATIRequestRepository(db)
    ati_request = await repo.get_by_id(request_id)
    
    if not ati_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATI request with ID '{request_id}' not found",
        )
    
    return _enrich_response(ati_request)


@router.get("/by-number/{request_number}", response_model=ATIRequestResponse)
async def get_ati_request_by_number(
    request_number: str,
    db: AsyncSession = Depends(get_db),
) -> ATIRequestResponse:
    """Get a specific ATI request by its public reference number."""
    repo = ATIRequestRepository(db)
    ati_request = await repo.get_by_request_number(request_number)
    
    if not ati_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATI request with number '{request_number}' not found",
        )
    
    return _enrich_response(ati_request)


@router.patch("/{request_id}", response_model=ATIRequestResponse)
async def update_ati_request(
    request_id: UUID,
    data: ATIRequestUpdate,
    db: AsyncSession = Depends(get_db),
) -> ATIRequestResponse:
    """Update an ATI request.
    
    Only provided fields will be updated (partial update).
    Common updates include:
    - **status**: Update request status
    - **outcome**: Set outcome when completed
    - **completion_date**: Set when request is completed
    - **extension_days**: Add extension days
    - **pages_processed/disclosed**: Update page counts
    - **fees_charged**: Update fees
    """
    repo = ATIRequestRepository(db)
    ati_request = await repo.get_by_id(request_id)
    
    if not ati_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATI request with ID '{request_id}' not found",
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Auto-set deemed refusal if completing past due date
    if "status" in update_data and update_data["status"] == RequestStatus.COMPLETED:
        completion = update_data.get("completion_date", date.today())
        if completion > ati_request.due_date:
            update_data["is_deemed_refusal"] = True
    
    updated = await repo.update(ati_request, update_data)
    return _enrich_response(updated)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ati_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an ATI request.
    
    Warning: This permanently removes the record. Consider updating status to 'abandoned' instead.
    """
    repo = ATIRequestRepository(db)
    ati_request = await repo.get_by_id(request_id)
    
    if not ati_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATI request with ID '{request_id}' not found",
        )
    
    await repo.delete(ati_request)
