"""Pydantic schemas for data ingestion operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecordErrorSchema(BaseModel):
    """Schema for a single record error."""
    
    row_number: int = Field(..., description="Row number where error occurred")
    field_name: Optional[str] = Field(None, description="Field that caused the error")
    error_message: str = Field(..., description="Description of the error")
    severity: str = Field(..., description="Error severity (warning, error, critical)")
    raw_value: Optional[str] = Field(None, description="Original value that caused the error")


class IngestionResultSchema(BaseModel):
    """Schema for ingestion operation result."""
    
    # Counts
    total_records: int = Field(..., description="Total records in source file")
    successful_records: int = Field(..., description="Records successfully processed")
    failed_records: int = Field(..., description="Records that failed validation")
    skipped_records: int = Field(..., description="Records skipped (e.g., duplicates)")
    
    # Statistics
    success_rate: float = Field(..., description="Percentage of successful records")
    duration_seconds: Optional[float] = Field(None, description="Processing time in seconds")
    
    # Source info
    source_file: Optional[str] = Field(None, description="Source file name")
    source_type: str = Field(..., description="Source type (csv, json, etc.)")
    
    # Status
    is_successful: bool = Field(..., description="Whether ingestion completed without critical errors")
    
    # Error summary
    error_count: int = Field(..., description="Total number of errors")
    warning_count: int = Field(..., description="Total number of warnings")
    errors: List[RecordErrorSchema] = Field(default_factory=list, description="First 50 errors")
    warnings: List[RecordErrorSchema] = Field(default_factory=list, description="First 50 warnings")
    
    # Created/Updated counts
    created_count: int = Field(..., description="Number of new records created")
    updated_count: int = Field(..., description="Number of existing records updated")


class IngestionOptionsSchema(BaseModel):
    """Schema for ingestion configuration options."""
    
    strict_mode: bool = Field(
        default=False, 
        description="Treat warnings as errors"
    )
    update_existing: bool = Field(
        default=False, 
        description="Update existing records instead of skipping"
    )
    batch_size: int = Field(
        default=100, 
        ge=1, 
        le=1000,
        description="Number of records to process per batch"
    )
    delimiter: Optional[str] = Field(
        None, 
        max_length=1,
        description="CSV delimiter (auto-detected if not provided)"
    )
    encoding: Optional[str] = Field(
        None,
        description="File encoding (auto-detected if not provided)"
    )


class FileUploadSchema(BaseModel):
    """Schema for file upload metadata."""
    
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")


class IngestionRequestSchema(BaseModel):
    """Schema for initiating an ingestion request."""
    
    file_info: FileUploadSchema
    options: IngestionOptionsSchema = Field(default_factory=IngestionOptionsSchema)
    data_type: str = Field(
        ..., 
        pattern="^(ati_requests|public_bodies)$",
        description="Type of data being ingested"
    )


class IngestionStatusSchema(BaseModel):
    """Schema for checking ingestion job status."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (pending, processing, completed, failed)")
    progress_percent: float = Field(default=0, ge=0, le=100, description="Processing progress")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    result: Optional[IngestionResultSchema] = Field(None, description="Final result if completed")
