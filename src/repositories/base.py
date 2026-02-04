"""Base repository class with common CRUD operations."""

from typing import Any, Generic, List, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations.
    
    Provides standard database operations that can be inherited
    by specific repository implementations.
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session
    
    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Create a new record.
        
        Args:
            obj_in: Dictionary of field values
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def get(self, id: UUID) -> ModelType | None:
        """Get a single record by ID.
        
        Args:
            id: UUID of the record
            
        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None
    ) -> List[ModelType]:
        """Get multiple records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional dictionary of filter conditions
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total records.
        
        Args:
            filters: Optional dictionary of filter conditions
            
        Returns:
            Total count of matching records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def update(self, id: UUID, obj_in: dict[str, Any]) -> ModelType | None:
        """Update a record by ID.
        
        Args:
            id: UUID of the record to update
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance or None if not found
        """
        db_obj = await self.get(id)
        if db_obj is None:
            return None
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID.
        
        Args:
            id: UUID of the record to delete
            
        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id)
        if db_obj is None:
            return False
        
        await self.session.delete(db_obj)
        await self.session.flush()
        return True
