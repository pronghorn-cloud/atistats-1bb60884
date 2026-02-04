"""API endpoints for data ingestion."""

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.ingestion import (
    IngestionResultSchema,
    IngestionOptionsSchema,
    RecordErrorSchema,
)
from src.services.ingestion import IngestionService

router = APIRouter()


def _convert_result_to_schema(result) -> IngestionResultSchema:
    """Convert IngestionResult to schema."""
    errors = [
        RecordErrorSchema(
            row_number=e.row_number,
            field_name=e.field_name,
            error_message=e.message,
            severity=e.severity,
            raw_value=e.raw_value,
        )
        for e in result.errors[:50]  # Limit to first 50
    ]
    
    warnings = [
        RecordErrorSchema(
            row_number=e.row_number,
            field_name=e.field_name,
            error_message=e.message,
            severity=e.severity,
            raw_value=e.raw_value,
        )
        for e in result.warnings[:50]  # Limit to first 50
    ]
    
    return IngestionResultSchema(
        total_records=result.total_records,
        successful_records=result.successful_records,
        failed_records=result.failed_records,
        skipped_records=result.skipped_records,
        success_rate=result.success_rate,
        duration_seconds=result.duration_seconds,
        source_file=result.source_file,
        source_type=result.source_type,
        is_successful=result.is_successful,
        error_count=result.error_count,
        warning_count=result.warning_count,
        errors=errors,
        warnings=warnings,
        created_count=result.created_count,
        updated_count=result.updated_count,
    )


@router.post("/ati-requests", response_model=IngestionResultSchema)
async def ingest_ati_requests(
    file: UploadFile = File(..., description="CSV file containing ATI requests"),
    strict_mode: bool = Form(False, description="Treat warnings as errors"),
    update_existing: bool = Form(False, description="Update existing records instead of skipping"),
    batch_size: int = Form(100, ge=1, le=1000, description="Records per batch"),
    delimiter: Optional[str] = Form(None, max_length=1, description="CSV delimiter"),
    encoding: Optional[str] = Form(None, description="File encoding"),
    db: AsyncSession = Depends(get_db),
) -> IngestionResultSchema:
    """Ingest ATI requests from a CSV file.
    
    The CSV file should contain columns that map to ATI request fields:
    - request_number (required): Public reference number
    - public_body_name or public_body_id (required): Reference to public body
    - submission_date (required): Date received (YYYY-MM-DD or various formats)
    - due_date (required): Statutory deadline
    - request_type: personal, non_personal, mixed, correction
    - status: received, in_progress, completed, etc.
    - outcome: full_disclosure, partial_disclosure, etc.
    - completion_date: When completed
    - extension_days: Number of extension days
    - summary: Description of request
    - pages_processed: Pages reviewed
    - pages_disclosed: Pages released
    - fees_charged: Fees amount
    
    Column names are flexible and will be automatically mapped.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported. Please upload a .csv file.",
        )
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )
    
    # Create options
    options = IngestionOptionsSchema(
        strict_mode=strict_mode,
        update_existing=update_existing,
        batch_size=batch_size,
        delimiter=delimiter,
        encoding=encoding,
    )
    
    # Run ingestion
    service = IngestionService(db)
    result = await service.ingest_ati_requests_from_csv(
        file_content=content,
        filename=file.filename,
        options=options.model_dump(),
    )
    
    return _convert_result_to_schema(result)


@router.post("/public-bodies", response_model=IngestionResultSchema)
async def ingest_public_bodies(
    file: UploadFile = File(..., description="CSV file containing public bodies"),
    strict_mode: bool = Form(False, description="Treat warnings as errors"),
    update_existing: bool = Form(False, description="Update existing records instead of skipping"),
    batch_size: int = Form(100, ge=1, le=1000, description="Records per batch"),
    delimiter: Optional[str] = Form(None, max_length=1, description="CSV delimiter"),
    encoding: Optional[str] = Form(None, description="File encoding"),
    db: AsyncSession = Depends(get_db),
) -> IngestionResultSchema:
    """Ingest public bodies from a CSV file.
    
    The CSV file should contain columns that map to public body fields:
    - name (required): Official name of the public body
    - abbreviation: Short form/acronym
    - description: Description of mandate
    - contact_email: Primary contact email
    - website_url: Official website URL
    
    Column names are flexible and will be automatically mapped.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported. Please upload a .csv file.",
        )
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )
    
    # Create options
    options = IngestionOptionsSchema(
        strict_mode=strict_mode,
        update_existing=update_existing,
        batch_size=batch_size,
        delimiter=delimiter,
        encoding=encoding,
    )
    
    # Run ingestion
    service = IngestionService(db)
    result = await service.ingest_public_bodies_from_csv(
        file_content=content,
        filename=file.filename,
        options=options.model_dump(),
    )
    
    return _convert_result_to_schema(result)


@router.get("/templates/{data_type}")
async def get_csv_template(
    data_type: str,
) -> dict:
    """Get a CSV template for data ingestion.
    
    Returns the expected column headers and example data for the specified data type.
    """
    if data_type == "ati-requests":
        return {
            "headers": [
                "request_number",
                "public_body_name",
                "submission_date",
                "due_date",
                "request_type",
                "status",
                "outcome",
                "completion_date",
                "extension_days",
                "summary",
                "pages_processed",
                "pages_disclosed",
                "fees_charged",
            ],
            "example_row": {
                "request_number": "ATI-2024-001",
                "public_body_name": "Department of Example",
                "submission_date": "2024-01-15",
                "due_date": "2024-02-14",
                "request_type": "non_personal",
                "status": "completed",
                "outcome": "full_disclosure",
                "completion_date": "2024-02-10",
                "extension_days": "0",
                "summary": "Request for budget documents",
                "pages_processed": "50",
                "pages_disclosed": "45",
                "fees_charged": "0.00",
            },
            "required_fields": ["request_number", "public_body_name", "submission_date", "due_date"],
        }
    elif data_type == "public-bodies":
        return {
            "headers": [
                "name",
                "abbreviation",
                "description",
                "contact_email",
                "website_url",
            ],
            "example_row": {
                "name": "Department of Example",
                "abbreviation": "DOE",
                "description": "Responsible for example matters",
                "contact_email": "ati@example.gov",
                "website_url": "https://example.gov",
            },
            "required_fields": ["name"],
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown data type: {data_type}. Use 'ati-requests' or 'public-bodies'.",
        )
