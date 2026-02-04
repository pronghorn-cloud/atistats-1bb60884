"""ATI Request model for tracking Access to Information requests."""

import uuid
import enum
from datetime import datetime, date
from typing import TYPE_CHECKING

from sqlalchemy import (
    String, Text, Boolean, Integer, Date, DateTime,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.public_body import PublicBody


class RequestStatus(enum.Enum):
    """Status of an ATI request throughout its lifecycle."""
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    PENDING_CLARIFICATION = "pending_clarification"
    EXTENDED = "extended"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    TRANSFERRED = "transferred"


class RequestType(enum.Enum):
    """Type of ATI request."""
    PERSONAL = "personal"  # Request for personal information
    NON_PERSONAL = "non_personal"  # Request for non-personal records
    MIXED = "mixed"  # Contains both personal and non-personal
    CORRECTION = "correction"  # Request to correct personal information


class RequestOutcome(enum.Enum):
    """Final outcome/disposition of an ATI request."""
    FULL_DISCLOSURE = "full_disclosure"
    PARTIAL_DISCLOSURE = "partial_disclosure"
    NO_DISCLOSURE = "no_disclosure"
    NO_RECORDS_EXIST = "no_records_exist"
    TRANSFERRED = "transferred"
    ABANDONED = "abandoned"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"  # Not yet determined


class ATIRequest(Base, TimestampMixin):
    """Model representing an Access to Information request.
    
    Attributes:
        id: Unique identifier for the request
        request_number: Public-facing reference number
        public_body_id: Foreign key to the handling public body
        submission_date: Date the request was received
        request_type: Type of ATI request
        status: Current status of the request
        outcome: Final disposition of the request
        due_date: Statutory deadline for response
        completion_date: Actual date of completion
        extension_days: Number of extension days taken
        summary: Brief description of the request
        pages_processed: Number of pages reviewed
        pages_disclosed: Number of pages released
        fees_charged: Amount of fees charged to requester
        is_deemed_refusal: Whether statutory deadline was missed
    """
    
    __tablename__ = "ati_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    request_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Foreign Keys
    public_body_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_bodies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Request Details
    submission_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    request_type: Mapped[RequestType] = mapped_column(
        SQLEnum(RequestType, name="request_type"),
        nullable=False,
        default=RequestType.NON_PERSONAL
    )
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status"),
        nullable=False,
        default=RequestStatus.RECEIVED,
        index=True
    )
    outcome: Mapped[RequestOutcome] = mapped_column(
        SQLEnum(RequestOutcome, name="request_outcome"),
        nullable=False,
        default=RequestOutcome.PENDING
    )
    
    # Timeline
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )
    completion_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )
    extension_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # Content Details
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    pages_processed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    pages_disclosed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Financial
    fees_charged: Mapped[float | None] = mapped_column(
        nullable=True
    )
    
    # Compliance Flags
    is_deemed_refusal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Relationships
    public_body: Mapped["PublicBody"] = relationship(
        "PublicBody",
        back_populates="ati_requests"
    )
    
    @property
    def response_days(self) -> int | None:
        """Calculate the number of days to respond to the request."""
        if self.completion_date:
            return (self.completion_date - self.submission_date).days
        return None
    
    @property
    def is_overdue(self) -> bool:
        """Check if the request is past its due date."""
        if self.status == RequestStatus.COMPLETED:
            return False
        return date.today() > self.due_date
    
    def __repr__(self) -> str:
        return f"<ATIRequest(id={self.id}, number='{self.request_number}', status={self.status.value})>"
