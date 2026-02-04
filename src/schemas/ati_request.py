"""Pydantic schemas for ATI Request data validation."""

from datetime import datetime, date
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.ati_request import RequestStatus, RequestType, RequestOutcome


class ATIRequestBase(BaseModel):
    """Base schema with common ATI request fields."""
    
    request_number: str = Field(..., min_length=1, max_length=100, description="Public reference number")
    public_body_id: UUID = Field(..., description="ID of the handling public body")
    submission_date: date = Field(..., description="Date the request was received")
    request_type: RequestType = Field(default=RequestType.NON_PERSONAL, description="Type of request")
    due_date: date = Field(..., description="Statutory deadline for response")
    summary: str | None = Field(None, description="Brief description of the request")


class ATIRequestCreate(ATIRequestBase):
    """Schema for creating a new ATI request."""
    
    status: RequestStatus = Field(default=RequestStatus.RECEIVED)
    outcome: RequestOutcome = Field(default=RequestOutcome.PENDING)
    extension_days: int = Field(default=0, ge=0)
    
    @field_validator('due_date')
    @classmethod
    def due_date_after_submission(cls, v: date, info) -> date:
        """Validate that due date is after submission date."""
        submission = info.data.get('submission_date')
        if submission and v < submission:
            raise ValueError('Due date must be on or after submission date')
        return v


class ATIRequestUpdate(BaseModel):
    """Schema for updating an existing ATI request.
    
    All fields are optional to support partial updates.
    """
    
    status: RequestStatus | None = None
    outcome: RequestOutcome | None = None
    due_date: date | None = None
    completion_date: date | None = None
    extension_days: int | None = Field(None, ge=0)
    summary: str | None = None
    pages_processed: int | None = Field(None, ge=0)
    pages_disclosed: int | None = Field(None, ge=0)
    fees_charged: float | None = Field(None, ge=0)
    is_deemed_refusal: bool | None = None


class ATIRequestResponse(ATIRequestBase):
    """Schema for ATI request response data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: RequestStatus
    outcome: RequestOutcome
    completion_date: date | None
    extension_days: int
    pages_processed: int | None
    pages_disclosed: int | None
    fees_charged: float | None
    is_deemed_refusal: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    response_days: int | None = None
    is_overdue: bool = False


class ATIRequestListResponse(BaseModel):
    """Schema for paginated list of ATI requests."""
    
    items: List[ATIRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
