"""Ingestion result and error tracking classes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Dict
from enum import Enum


class ErrorSeverity(Enum):
    """Severity level for ingestion errors."""
    WARNING = "warning"  # Record processed with modifications
    ERROR = "error"  # Record skipped
    CRITICAL = "critical"  # Ingestion stopped


@dataclass
class RecordError:
    """Represents an error encountered during record processing."""
    row_number: int
    field_name: str | None
    error_message: str
    severity: ErrorSeverity
    raw_value: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "row_number": self.row_number,
            "field_name": self.field_name,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "raw_value": str(self.raw_value) if self.raw_value is not None else None,
        }


@dataclass
class IngestionResult:
    """Result of a data ingestion operation."""
    
    # Counts
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    # Details
    source_file: str | None = None
    source_type: str = "unknown"
    errors: List[RecordError] = field(default_factory=list)
    warnings: List[RecordError] = field(default_factory=list)
    
    # Created record IDs for reference
    created_ids: List[str] = field(default_factory=list)
    updated_ids: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.successful_records / self.total_records) * 100
    
    @property
    def duration_seconds(self) -> float | None:
        """Calculate the duration of the ingestion in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def is_successful(self) -> bool:
        """Check if ingestion completed without critical errors."""
        return not any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def add_error(self, row: int, field: str | None, message: str, 
                  severity: ErrorSeverity = ErrorSeverity.ERROR, raw_value: Any = None) -> None:
        """Add an error to the result."""
        error = RecordError(
            row_number=row,
            field_name=field,
            error_message=message,
            severity=severity,
            raw_value=raw_value
        )
        if severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)
    
    def mark_complete(self) -> None:
        """Mark the ingestion as complete."""
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total_records": self.total_records,
            "successful_records": self.successful_records,
            "failed_records": self.failed_records,
            "skipped_records": self.skipped_records,
            "success_rate": round(self.success_rate, 2),
            "duration_seconds": self.duration_seconds,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "is_successful": self.is_successful,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors[:50]],  # Limit errors in response
            "warnings": [w.to_dict() for w in self.warnings[:50]],
            "created_count": len(self.created_ids),
            "updated_count": len(self.updated_ids),
        }
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"Ingestion Result: {self.source_file or 'Unknown source'}",
            f"  Total Records: {self.total_records}",
            f"  Successful: {self.successful_records}",
            f"  Failed: {self.failed_records}",
            f"  Skipped: {self.skipped_records}",
            f"  Success Rate: {self.success_rate:.1f}%",
        ]
        if self.duration_seconds:
            lines.append(f"  Duration: {self.duration_seconds:.2f}s")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        if self.warnings:
            lines.append(f"  Warnings: {len(self.warnings)}")
        return "\n".join(lines)
