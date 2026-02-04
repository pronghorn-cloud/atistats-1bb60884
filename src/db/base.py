"""SQLAlchemy base class for declarative models."""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
