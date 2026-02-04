"""Main ingestion service for ATI data."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ati_request import ATIRequest, RequestStatus, RequestType, RequestOutcome
from src.models.public_body import PublicBody
from src.repositories.ati_request import ATIRequestRepository
from src.repositories.public_body import PublicBodyRepository
from src.schemas.ati_request import ATIRequestCreate
from src.schemas.public_body import PublicBodyCreate
from src.services.ingestion.csv_parser import CSVParser, CSVParseError
from src.services.ingestion.validators import DataValidator
from src.services.ingestion.transformers import DataTransformer
from src.services.ingestion.result import IngestionResult, ErrorSeverity


logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when ingestion fails."""
    pass


class IngestionService:
    """Service for ingesting ATI request data from various sources.
    
    Provides a complete pipeline for:
    1. Parsing source files (CSV)
    2. Transforming data to standard format
    3. Validating data integrity
    4. Storing in database
    5. Tracking results and errors
    """
    
    def __init__(
        self,
        session: AsyncSession,
        strict_mode: bool = False,
        batch_size: int = 100,
        update_existing: bool = False,
    ):
        """Initialize ingestion service.
        
        Args:
            session: Database session for persistence
            strict_mode: If True, warnings become errors
            batch_size: Number of records to commit per batch
            update_existing: If True, update existing records instead of skipping
        """
        self.session = session
        self.strict_mode = strict_mode
        self.batch_size = batch_size
        self.update_existing = update_existing
        
        # Initialize components
        self.parser = CSVParser()
        self.transformer = DataTransformer()
        self.validator = DataValidator(strict_mode=strict_mode)
        
        # Repositories
        self.ati_repo = ATIRequestRepository(session)
        self.public_body_repo = PublicBodyRepository(session)
        
        # Cache for public body lookups
        self._public_body_cache: Dict[str, UUID] = {}
    
    async def ingest_ati_requests_from_csv(
        self,
        file_path: Optional[Union[str, Path]] = None,
        file_content: Optional[bytes] = None,
        filename: str = "upload.csv",
    ) -> IngestionResult:
        """Ingest ATI requests from a CSV file.
        
        Args:
            file_path: Path to CSV file (mutually exclusive with file_content)
            file_content: Raw CSV content as bytes
            filename: Original filename for tracking
            
        Returns:
            IngestionResult with statistics and errors
        """
        result = IngestionResult(
            source_file=filename,
            source_type="csv",
        )
        
        try:
            # Parse CSV
            if file_path:
                records = self.parser.parse_file(file_path)
                result.source_file = str(file_path)
            elif file_content:
                records = self.parser.parse_bytes(file_content, filename=filename)
            else:
                raise IngestionError("Either file_path or file_content must be provided")
            
            result.total_records = len(records)
            logger.info(f"Parsed {result.total_records} records from {filename}")
            
            # Load public body cache
            await self._load_public_body_cache()
            
            # Process records in batches
            batch = []
            for record in records:
                row_num = record.pop('_row_number', 0)
                
                # Transform
                transformed = self.transformer.transform_ati_request(record)
                
                # Validate
                is_valid, cleaned = self.validator.validate_ati_request(transformed, row_num)
                
                # Collect validation errors/warnings
                for error in self.validator.errors:
                    result.errors.append(error)
                for warning in self.validator.warnings:
                    result.warnings.append(warning)
                
                if not is_valid:
                    result.failed_records += 1
                    continue
                
                # Resolve public body
                try:
                    public_body_id = await self._resolve_public_body(
                        cleaned.get('public_body_id'),
                        cleaned.get('public_body_name'),
                        row_num,
                        result
                    )
                    if not public_body_id:
                        result.failed_records += 1
                        continue
                    cleaned['public_body_id'] = public_body_id
                except Exception as e:
                    result.add_error(row_num, 'public_body', str(e), ErrorSeverity.ERROR)
                    result.failed_records += 1
                    continue
                
                # Check for duplicates
                existing = await self.ati_repo.get_by_request_number(
                    cleaned['request_number']
                )
                
                if existing:
                    if self.update_existing:
                        # Update existing record
                        try:
                            await self._update_ati_request(existing, cleaned)
                            result.updated_ids.append(str(existing.id))
                            result.successful_records += 1
                        except Exception as e:
                            result.add_error(row_num, None, f"Update failed: {e}", ErrorSeverity.ERROR)
                            result.failed_records += 1
                    else:
                        result.add_error(
                            row_num, 'request_number',
                            f"Duplicate request number: {cleaned['request_number']}",
                            ErrorSeverity.WARNING
                        )
                        result.skipped_records += 1
                    continue
                
                # Prepare for insert
                batch.append((row_num, cleaned))
                
                # Commit batch if full
                if len(batch) >= self.batch_size:
                    await self._commit_batch(batch, result)
                    batch = []
            
            # Commit remaining records
            if batch:
                await self._commit_batch(batch, result)
            
            # Final commit
            await self.session.commit()
            
        except CSVParseError as e:
            result.add_error(0, None, f"CSV parsing failed: {e}", ErrorSeverity.CRITICAL)
            logger.error(f"CSV parsing failed: {e}")
        except Exception as e:
            result.add_error(0, None, f"Ingestion failed: {e}", ErrorSeverity.CRITICAL)
            logger.exception(f"Ingestion failed: {e}")
            await self.session.rollback()
        finally:
            result.mark_complete()
        
        logger.info(result.summary())
        return result
    
    async def ingest_public_bodies_from_csv(
        self,
        file_path: Optional[Union[str, Path]] = None,
        file_content: Optional[bytes] = None,
        filename: str = "public_bodies.csv",
    ) -> IngestionResult:
        """Ingest public bodies from a CSV file.
        
        Args:
            file_path: Path to CSV file
            file_content: Raw CSV content as bytes
            filename: Original filename for tracking
            
        Returns:
            IngestionResult with statistics and errors
        """
        result = IngestionResult(
            source_file=filename,
            source_type="csv",
        )
        
        try:
            # Parse CSV
            if file_path:
                records = self.parser.parse_file(file_path)
                result.source_file = str(file_path)
            elif file_content:
                records = self.parser.parse_bytes(file_content, filename=filename)
            else:
                raise IngestionError("Either file_path or file_content must be provided")
            
            result.total_records = len(records)
            logger.info(f"Parsed {result.total_records} public body records from {filename}")
            
            for record in records:
                row_num = record.pop('_row_number', 0)
                
                # Transform
                transformed = self.transformer.transform_public_body(record)
                
                # Validate
                is_valid, cleaned = self.validator.validate_public_body(transformed, row_num)
                
                # Collect validation errors/warnings
                for error in self.validator.errors:
                    result.errors.append(error)
                for warning in self.validator.warnings:
                    result.warnings.append(warning)
                
                if not is_valid:
                    result.failed_records += 1
                    continue
                
                # Check for duplicates
                existing = await self.public_body_repo.get_by_name(cleaned['name'])
                
                if existing:
                    if self.update_existing:
                        try:
                            await self._update_public_body(existing, cleaned)
                            result.updated_ids.append(str(existing.id))
                            result.successful_records += 1
                        except Exception as e:
                            result.add_error(row_num, None, f"Update failed: {e}", ErrorSeverity.ERROR)
                            result.failed_records += 1
                    else:
                        result.add_error(
                            row_num, 'name',
                            f"Duplicate public body: {cleaned['name']}",
                            ErrorSeverity.WARNING
                        )
                        result.skipped_records += 1
                    continue
                
                # Create new public body
                try:
                    public_body = await self._create_public_body(cleaned)
                    result.created_ids.append(str(public_body.id))
                    result.successful_records += 1
                except Exception as e:
                    result.add_error(row_num, None, f"Creation failed: {e}", ErrorSeverity.ERROR)
                    result.failed_records += 1
            
            # Commit all changes
            await self.session.commit()
            
        except CSVParseError as e:
            result.add_error(0, None, f"CSV parsing failed: {e}", ErrorSeverity.CRITICAL)
            logger.error(f"CSV parsing failed: {e}")
        except Exception as e:
            result.add_error(0, None, f"Ingestion failed: {e}", ErrorSeverity.CRITICAL)
            logger.exception(f"Ingestion failed: {e}")
            await self.session.rollback()
        finally:
            result.mark_complete()
        
        logger.info(result.summary())
        return result
    
    async def _load_public_body_cache(self) -> None:
        """Load public body name -> ID mapping into cache."""
        public_bodies = await self.public_body_repo.get_all()
        self._public_body_cache = {
            pb.name.lower(): pb.id for pb in public_bodies
        }
        # Also add abbreviations
        for pb in public_bodies:
            if pb.abbreviation:
                self._public_body_cache[pb.abbreviation.lower()] = pb.id
    
    async def _resolve_public_body(
        self,
        public_body_id: Optional[str],
        public_body_name: Optional[str],
        row_num: int,
        result: IngestionResult,
    ) -> Optional[UUID]:
        """Resolve public body to UUID.
        
        Args:
            public_body_id: UUID string if provided
            public_body_name: Name to look up
            row_num: Row number for error reporting
            result: Result object for error tracking
            
        Returns:
            UUID of public body or None if not found
        """
        # Try ID first
        if public_body_id:
            try:
                return UUID(str(public_body_id))
            except ValueError:
                pass
        
        # Try name lookup
        if public_body_name:
            name_lower = public_body_name.lower().strip()
            
            # Check cache
            if name_lower in self._public_body_cache:
                return self._public_body_cache[name_lower]
            
            # Try database lookup
            public_body = await self.public_body_repo.get_by_name(public_body_name)
            if public_body:
                self._public_body_cache[name_lower] = public_body.id
                return public_body.id
            
            # Not found - could auto-create here if desired
            result.add_error(
                row_num, 'public_body',
                f"Public body not found: {public_body_name}",
                ErrorSeverity.ERROR
            )
            return None
        
        result.add_error(
            row_num, 'public_body',
            "No public body ID or name provided",
            ErrorSeverity.ERROR
        )
        return None
    
    async def _commit_batch(
        self,
        batch: List[tuple],
        result: IngestionResult,
    ) -> None:
        """Commit a batch of ATI request records.
        
        Args:
            batch: List of (row_num, cleaned_data) tuples
            result: Result object for tracking
        """
        for row_num, cleaned in batch:
            try:
                ati_request = await self._create_ati_request(cleaned)
                result.created_ids.append(str(ati_request.id))
                result.successful_records += 1
            except Exception as e:
                result.add_error(row_num, None, f"Creation failed: {e}", ErrorSeverity.ERROR)
                result.failed_records += 1
        
        # Flush but don't commit yet
        await self.session.flush()
    
    async def _create_ati_request(self, data: Dict[str, Any]) -> ATIRequest:
        """Create a new ATI request record."""
        # Map enum values
        request_type = RequestType(data['request_type']) if data.get('request_type') else RequestType.NON_PERSONAL
        status = RequestStatus(data['status']) if data.get('status') else RequestStatus.RECEIVED
        outcome = RequestOutcome(data['outcome']) if data.get('outcome') else RequestOutcome.PENDING
        
        ati_request = ATIRequest(
            request_number=data['request_number'],
            public_body_id=data['public_body_id'],
            submission_date=data['submission_date'],
            due_date=data['due_date'],
            request_type=request_type,
            status=status,
            outcome=outcome,
            completion_date=data.get('completion_date'),
            extension_days=data.get('extension_days', 0),
            summary=data.get('summary'),
            pages_processed=data.get('pages_processed'),
            pages_disclosed=data.get('pages_disclosed'),
            fees_charged=data.get('fees_charged'),
            is_deemed_refusal=data.get('is_deemed_refusal', False),
        )
        
        self.session.add(ati_request)
        return ati_request
    
    async def _update_ati_request(self, existing: ATIRequest, data: Dict[str, Any]) -> ATIRequest:
        """Update an existing ATI request record."""
        # Update fields that are provided
        if data.get('status'):
            existing.status = RequestStatus(data['status'])
        if data.get('outcome'):
            existing.outcome = RequestOutcome(data['outcome'])
        if data.get('completion_date'):
            existing.completion_date = data['completion_date']
        if data.get('extension_days') is not None:
            existing.extension_days = data['extension_days']
        if data.get('pages_processed') is not None:
            existing.pages_processed = data['pages_processed']
        if data.get('pages_disclosed') is not None:
            existing.pages_disclosed = data['pages_disclosed']
        if data.get('fees_charged') is not None:
            existing.fees_charged = data['fees_charged']
        if data.get('is_deemed_refusal') is not None:
            existing.is_deemed_refusal = data['is_deemed_refusal']
        if data.get('summary'):
            existing.summary = data['summary']
        
        return existing
    
    async def _create_public_body(self, data: Dict[str, Any]) -> PublicBody:
        """Create a new public body record."""
        public_body = PublicBody(
            name=data['name'],
            abbreviation=data.get('abbreviation'),
            description=data.get('description'),
            contact_email=data.get('contact_email'),
            website_url=data.get('website_url'),
            is_active=data.get('is_active', True),
        )
        
        self.session.add(public_body)
        await self.session.flush()  # Get the ID
        
        # Update cache
        self._public_body_cache[public_body.name.lower()] = public_body.id
        if public_body.abbreviation:
            self._public_body_cache[public_body.abbreviation.lower()] = public_body.id
        
        return public_body
    
    async def _update_public_body(self, existing: PublicBody, data: Dict[str, Any]) -> PublicBody:
        """Update an existing public body record."""
        if data.get('abbreviation'):
            existing.abbreviation = data['abbreviation']
        if data.get('description'):
            existing.description = data['description']
        if data.get('contact_email'):
            existing.contact_email = data['contact_email']
        if data.get('website_url'):
            existing.website_url = data['website_url']
        if data.get('is_active') is not None:
            existing.is_active = data['is_active']
        
        return existing
