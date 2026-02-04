"""Public Body model for organizations that handle ATI requests."""

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.ati_request import ATIRequest


class PublicBody(Base, TimestampMixin):
    """Model representing a public body/organization that processes ATI requests.
    
    Attributes:
        id: Unique identifier for the public body
        name: Official name of the public body
        abbreviation: Short form/acronym of the public body name
        description: Description of the public body's mandate
        contact_email: Primary contact email for ATI requests
        website_url: Official website URL
        is_active: Whether the public body is currently active
    """
    
    __tablename__ = "public_bodies"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )
    abbreviation: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    website_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # Relationships
    ati_requests: Mapped[List["ATIRequest"]] = relationship(
        "ATIRequest",
        back_populates="public_body",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<PublicBody(id={self.id}, name='{self.name}')>"
