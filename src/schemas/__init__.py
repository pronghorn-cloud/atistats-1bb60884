"""Pydantic schemas package for request/response validation."""

from src.schemas.public_body import (
    PublicBodyCreate,
    PublicBodyUpdate,
    PublicBodyResponse,
    PublicBodyListResponse,
)
from src.schemas.ati_request import (
    ATIRequestCreate,
    ATIRequestUpdate,
    ATIRequestResponse,
    ATIRequestListResponse,
)
from src.schemas.ingestion import (
    RecordErrorSchema,
    IngestionResultSchema,
    IngestionOptionsSchema,
    FileUploadSchema,
    IngestionRequestSchema,
    IngestionStatusSchema,
)

__all__ = [
    # Public Body schemas
    "PublicBodyCreate",
    "PublicBodyUpdate",
    "PublicBodyResponse",
    "PublicBodyListResponse",
    # ATI Request schemas
    "ATIRequestCreate",
    "ATIRequestUpdate",
    "ATIRequestResponse",
    "ATIRequestListResponse",
    # Ingestion schemas
    "RecordErrorSchema",
    "IngestionResultSchema",
    "IngestionOptionsSchema",
    "FileUploadSchema",
    "IngestionRequestSchema",
    "IngestionStatusSchema",
]
