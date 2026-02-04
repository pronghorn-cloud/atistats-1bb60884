"""Repository for ATI Request data access."""

from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.ati_request import ATIRequest, RequestStatus, RequestOutcome
from src.repositories.base import BaseRepository


class ATIRequestRepository(BaseRepository[ATIRequest]):
    """Repository for ATI Request CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        super().__init__(ATIRequest, session)
    
    async def get_by_request_number(self, request_number: str) -> ATIRequest | None:
        """Get an ATI request by its public reference number.
        
        Args:
            request_number: Public reference number
            
        Returns:
            ATIRequest instance or None if not found
        """
        result = await self.session.execute(
            select(ATIRequest)
            .where(ATIRequest.request_number == request_number)
            .options(selectinload(ATIRequest.public_body))
        )
        return result.scalar_one_or_none()
    
    async def get_by_public_body(
        self,
        public_body_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        status: RequestStatus | None = None
    ) -> List[ATIRequest]:
        """Get ATI requests for a specific public body.
        
        Args:
            public_body_id: UUID of the public body
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of ATIRequest instances
        """
        query = select(ATIRequest).where(
            ATIRequest.public_body_id == public_body_id
        )
        
        if status:
            query = query.where(ATIRequest.status == status)
        
        result = await self.session.execute(
            query
            .offset(skip)
            .limit(limit)
            .order_by(ATIRequest.submission_date.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ATIRequest]:
        """Get ATI requests within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of ATIRequest instances
        """
        result = await self.session.execute(
            select(ATIRequest)
            .where(
                and_(
                    ATIRequest.submission_date >= start_date,
                    ATIRequest.submission_date <= end_date
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(ATIRequest.submission_date.desc())
        )
        return list(result.scalars().all())
    
    async def get_overdue(self, skip: int = 0, limit: int = 100) -> List[ATIRequest]:
        """Get all overdue ATI requests.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of overdue ATIRequest instances
        """
        today = date.today()
        result = await self.session.execute(
            select(ATIRequest)
            .where(
                and_(
                    ATIRequest.due_date < today,
                    ATIRequest.status != RequestStatus.COMPLETED,
                    ATIRequest.status != RequestStatus.ABANDONED
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(ATIRequest.due_date)
            .options(selectinload(ATIRequest.public_body))
        )
        return list(result.scalars().all())
    
    async def count_by_status(self, public_body_id: UUID | None = None) -> dict[RequestStatus, int]:
        """Count requests grouped by status.
        
        Args:
            public_body_id: Optional filter by public body
            
        Returns:
            Dictionary mapping status to count
        """
        query = select(
            ATIRequest.status,
            func.count(ATIRequest.id)
        ).group_by(ATIRequest.status)
        
        if public_body_id:
            query = query.where(ATIRequest.public_body_id == public_body_id)
        
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}
    
    async def count_by_outcome(self, public_body_id: UUID | None = None) -> dict[RequestOutcome, int]:
        """Count completed requests grouped by outcome.
        
        Args:
            public_body_id: Optional filter by public body
            
        Returns:
            Dictionary mapping outcome to count
        """
        query = select(
            ATIRequest.outcome,
            func.count(ATIRequest.id)
        ).where(
            ATIRequest.status == RequestStatus.COMPLETED
        ).group_by(ATIRequest.outcome)
        
        if public_body_id:
            query = query.where(ATIRequest.public_body_id == public_body_id)
        
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}
    
    async def calculate_average_response_time(
        self,
        public_body_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None
    ) -> float | None:
        """Calculate average response time in days for completed requests.
        
        Args:
            public_body_id: Optional filter by public body
            start_date: Optional start of date range
            end_date: Optional end of date range
            
        Returns:
            Average response time in days or None if no data
        """
        query = select(
            func.avg(
                func.extract('day', ATIRequest.completion_date) -
                func.extract('day', ATIRequest.submission_date)
            )
        ).where(
            and_(
                ATIRequest.status == RequestStatus.COMPLETED,
                ATIRequest.completion_date.isnot(None)
            )
        )
        
        if public_body_id:
            query = query.where(ATIRequest.public_body_id == public_body_id)
        
        if start_date:
            query = query.where(ATIRequest.submission_date >= start_date)
        
        if end_date:
            query = query.where(ATIRequest.submission_date <= end_date)
        
        result = await self.session.execute(query)
        avg = result.scalar_one_or_none()
        return float(avg) if avg else None
