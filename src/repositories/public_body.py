"""Repository for Public Body data access."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.public_body import PublicBody
from src.repositories.base import BaseRepository


class PublicBodyRepository(BaseRepository[PublicBody]):
    """Repository for Public Body CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        super().__init__(PublicBody, session)
    
    async def get_by_name(self, name: str) -> PublicBody | None:
        """Get a public body by its name.
        
        Args:
            name: Name of the public body
            
        Returns:
            PublicBody instance or None if not found
        """
        result = await self.session.execute(
            select(PublicBody).where(PublicBody.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_abbreviation(self, abbreviation: str) -> PublicBody | None:
        """Get a public body by its abbreviation.
        
        Args:
            abbreviation: Abbreviation/acronym of the public body
            
        Returns:
            PublicBody instance or None if not found
        """
        result = await self.session.execute(
            select(PublicBody).where(PublicBody.abbreviation == abbreviation)
        )
        return result.scalar_one_or_none()
    
    async def get_active(self, skip: int = 0, limit: int = 100) -> List[PublicBody]:
        """Get all active public bodies.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active PublicBody instances
        """
        result = await self.session.execute(
            select(PublicBody)
            .where(PublicBody.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(PublicBody.name)
        )
        return list(result.scalars().all())
    
    async def search_by_name(self, query: str, limit: int = 20) -> List[PublicBody]:
        """Search public bodies by name (case-insensitive partial match).
        
        Args:
            query: Search string
            limit: Maximum number of results
            
        Returns:
            List of matching PublicBody instances
        """
        result = await self.session.execute(
            select(PublicBody)
            .where(PublicBody.name.ilike(f"%{query}%"))
            .where(PublicBody.is_active == True)
            .limit(limit)
            .order_by(PublicBody.name)
        )
        return list(result.scalars().all())
