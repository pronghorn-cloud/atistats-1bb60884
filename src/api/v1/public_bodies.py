"""API endpoints for Public Bodies."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.repositories.public_body import PublicBodyRepository
from src.schemas.public_body import (
    PublicBodyCreate,
    PublicBodyUpdate,
    PublicBodyResponse,
    PublicBodyListResponse,
)

router = APIRouter()


@router.get("", response_model=PublicBodyListResponse)
async def list_public_bodies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, min_length=1, description="Search by name"),
    active_only: bool = Query(True, description="Only return active public bodies"),
    db: AsyncSession = Depends(get_db),
) -> PublicBodyListResponse:
    """List all public bodies with pagination and optional search.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **search**: Optional search term to filter by name
    - **active_only**: If true, only return active public bodies
    """
    repo = PublicBodyRepository(db)
    skip = (page - 1) * page_size
    
    if search:
        items = await repo.search_by_name(search, limit=page_size)
        total = len(items)  # For search, we return all matches up to limit
    elif active_only:
        items = await repo.get_active(skip=skip, limit=page_size)
        total = await repo.count()
    else:
        items = await repo.get_many(skip=skip, limit=page_size)
        total = await repo.count()
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return PublicBodyListResponse(
        items=[PublicBodyResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=PublicBodyResponse, status_code=status.HTTP_201_CREATED)
async def create_public_body(
    data: PublicBodyCreate,
    db: AsyncSession = Depends(get_db),
) -> PublicBodyResponse:
    """Create a new public body.
    
    - **name**: Official name of the public body (required)
    - **abbreviation**: Short form/acronym (optional)
    - **description**: Description of mandate (optional)
    - **contact_email**: Primary contact email (optional)
    - **website_url**: Official website URL (optional)
    """
    repo = PublicBodyRepository(db)
    
    # Check if name already exists
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Public body with name '{data.name}' already exists",
        )
    
    # Check if abbreviation already exists (if provided)
    if data.abbreviation:
        existing_abbrev = await repo.get_by_abbreviation(data.abbreviation)
        if existing_abbrev:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Public body with abbreviation '{data.abbreviation}' already exists",
            )
    
    public_body = await repo.create(data.model_dump())
    return PublicBodyResponse.model_validate(public_body)


@router.get("/{public_body_id}", response_model=PublicBodyResponse)
async def get_public_body(
    public_body_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PublicBodyResponse:
    """Get a specific public body by ID."""
    repo = PublicBodyRepository(db)
    public_body = await repo.get_by_id(public_body_id)
    
    if not public_body:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public body with ID '{public_body_id}' not found",
        )
    
    return PublicBodyResponse.model_validate(public_body)


@router.patch("/{public_body_id}", response_model=PublicBodyResponse)
async def update_public_body(
    public_body_id: UUID,
    data: PublicBodyUpdate,
    db: AsyncSession = Depends(get_db),
) -> PublicBodyResponse:
    """Update a public body.
    
    Only provided fields will be updated (partial update).
    """
    repo = PublicBodyRepository(db)
    public_body = await repo.get_by_id(public_body_id)
    
    if not public_body:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public body with ID '{public_body_id}' not found",
        )
    
    # Check for name conflict if name is being updated
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = await repo.get_by_name(update_data["name"])
        if existing and existing.id != public_body_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Public body with name '{update_data['name']}' already exists",
            )
    
    # Check for abbreviation conflict if abbreviation is being updated
    if "abbreviation" in update_data and update_data["abbreviation"]:
        existing_abbrev = await repo.get_by_abbreviation(update_data["abbreviation"])
        if existing_abbrev and existing_abbrev.id != public_body_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Public body with abbreviation '{update_data['abbreviation']}' already exists",
            )
    
    updated = await repo.update(public_body, update_data)
    return PublicBodyResponse.model_validate(updated)


@router.delete("/{public_body_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_public_body(
    public_body_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a public body.
    
    Note: This will fail if there are ATI requests associated with this public body.
    Consider deactivating instead using PATCH with `is_active: false`.
    """
    repo = PublicBodyRepository(db)
    public_body = await repo.get_by_id(public_body_id)
    
    if not public_body:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public body with ID '{public_body_id}' not found",
        )
    
    await repo.delete(public_body)
