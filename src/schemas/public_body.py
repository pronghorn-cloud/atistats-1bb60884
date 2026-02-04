"""Pydantic schemas for Public Body data validation."""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl, Field


class PublicBodyBase(BaseModel):
    """Base schema with common public body fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Official name of the public body")
    abbreviation: str | None = Field(None, max_length=50, description="Short form/acronym")
    description: str | None = Field(None, description="Description of the public body's mandate")
    contact_email: EmailStr | None = Field(None, description="Primary contact email")
    website_url: str | None = Field(None, max_length=500, description="Official website URL")


class PublicBodyCreate(PublicBodyBase):
    """Schema for creating a new public body."""
    pass


class PublicBodyUpdate(BaseModel):
    """Schema for updating an existing public body.
    
    All fields are optional to support partial updates.
    """
    
    name: str | None = Field(None, min_length=1, max_length=255)
    abbreviation: str | None = Field(None, max_length=50)
    description: str | None = None
    contact_email: EmailStr | None = None
    website_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class PublicBodyResponse(PublicBodyBase):
    """Schema for public body response data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PublicBodyListResponse(BaseModel):
    """Schema for paginated list of public bodies."""
    
    items: List[PublicBodyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
