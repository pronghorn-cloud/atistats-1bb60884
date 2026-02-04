"""Data validation logic for ATI request ingestion."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Tuple, Optional
from uuid import UUID

from src.models.ati_request import RequestStatus, RequestType, RequestOutcome
from src.services.ingestion.result import RecordError, ErrorSeverity


class ValidationError(Exception):
    """Raised when validation fails for a record."""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class DataValidator:
    """Validates data records before ingestion."""
    
    # Valid enum values for mapping
    VALID_STATUS_VALUES = {s.value for s in RequestStatus}
    VALID_TYPE_VALUES = {t.value for t in RequestType}
    VALID_OUTCOME_VALUES = {o.value for o in RequestOutcome}
    
    # Common date formats to try
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    
    def __init__(self, strict_mode: bool = False):
        """Initialize validator.
        
        Args:
            strict_mode: If True, any validation warning becomes an error
        """
        self.strict_mode = strict_mode
        self.errors: List[RecordError] = []
        self.warnings: List[RecordError] = []
    
    def reset(self) -> None:
        """Reset validation state for new record."""
        self.errors = []
        self.warnings = []
    
    def validate_ati_request(self, data: Dict[str, Any], row_number: int) -> Tuple[bool, Dict[str, Any]]:
        """Validate an ATI request record.
        
        Args:
            data: Raw record data
            row_number: Row number for error reporting
            
        Returns:
            Tuple of (is_valid, cleaned_data)
        """
        self.reset()
        cleaned = {}
        
        # Required fields
        cleaned['request_number'] = self._validate_request_number(
            data.get('request_number'), row_number
        )
        cleaned['submission_date'] = self._validate_date(
            data.get('submission_date'), 'submission_date', row_number, required=True
        )
        cleaned['due_date'] = self._validate_date(
            data.get('due_date'), 'due_date', row_number, required=True
        )
        
        # Public body reference (can be ID or name for lookup)
        cleaned['public_body_id'] = data.get('public_body_id')
        cleaned['public_body_name'] = data.get('public_body_name') or data.get('public_body')
        
        if not cleaned['public_body_id'] and not cleaned['public_body_name']:
            self._add_error(row_number, 'public_body', 'Either public_body_id or public_body_name is required')
        
        # Enum fields with defaults
        cleaned['request_type'] = self._validate_enum(
            data.get('request_type'), 'request_type', self.VALID_TYPE_VALUES,
            row_number, default='non_personal'
        )
        cleaned['status'] = self._validate_enum(
            data.get('status'), 'status', self.VALID_STATUS_VALUES,
            row_number, default='received'
        )
        cleaned['outcome'] = self._validate_enum(
            data.get('outcome'), 'outcome', self.VALID_OUTCOME_VALUES,
            row_number, default='pending'
        )
        
        # Optional date
        cleaned['completion_date'] = self._validate_date(
            data.get('completion_date'), 'completion_date', row_number, required=False
        )
        
        # Optional integer fields
        cleaned['extension_days'] = self._validate_integer(
            data.get('extension_days'), 'extension_days', row_number, min_val=0, default=0
        )
        cleaned['pages_processed'] = self._validate_integer(
            data.get('pages_processed'), 'pages_processed', row_number, min_val=0
        )
        cleaned['pages_disclosed'] = self._validate_integer(
            data.get('pages_disclosed'), 'pages_disclosed', row_number, min_val=0
        )
        
        # Optional float
        cleaned['fees_charged'] = self._validate_float(
            data.get('fees_charged'), 'fees_charged', row_number, min_val=0.0
        )
        
        # Optional boolean
        cleaned['is_deemed_refusal'] = self._validate_boolean(
            data.get('is_deemed_refusal'), 'is_deemed_refusal', row_number, default=False
        )
        
        # Optional text
        cleaned['summary'] = self._validate_string(
            data.get('summary'), 'summary', row_number, max_length=10000
        )
        
        # Cross-field validation
        self._validate_date_logic(cleaned, row_number)
        self._validate_page_logic(cleaned, row_number)
        
        is_valid = len(self.errors) == 0
        return is_valid, cleaned
    
    def validate_public_body(self, data: Dict[str, Any], row_number: int) -> Tuple[bool, Dict[str, Any]]:
        """Validate a public body record.
        
        Args:
            data: Raw record data
            row_number: Row number for error reporting
            
        Returns:
            Tuple of (is_valid, cleaned_data)
        """
        self.reset()
        cleaned = {}
        
        # Required fields
        cleaned['name'] = self._validate_string(
            data.get('name'), 'name', row_number, required=True, max_length=255
        )
        
        # Optional fields
        cleaned['abbreviation'] = self._validate_string(
            data.get('abbreviation'), 'abbreviation', row_number, max_length=50
        )
        cleaned['description'] = self._validate_string(
            data.get('description'), 'description', row_number
        )
        cleaned['contact_email'] = self._validate_email(
            data.get('contact_email'), 'contact_email', row_number
        )
        cleaned['website_url'] = self._validate_url(
            data.get('website_url'), 'website_url', row_number
        )
        cleaned['is_active'] = self._validate_boolean(
            data.get('is_active'), 'is_active', row_number, default=True
        )
        
        is_valid = len(self.errors) == 0
        return is_valid, cleaned
    
    def _validate_request_number(self, value: Any, row: int) -> Optional[str]:
        """Validate request number format."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self._add_error(row, 'request_number', 'Request number is required')
            return None
        
        value = str(value).strip()
        if len(value) > 100:
            self._add_error(row, 'request_number', f'Request number too long (max 100 chars)', value)
            return None
        
        return value
    
    def _validate_date(self, value: Any, field: str, row: int, 
                       required: bool = False) -> Optional[date]:
        """Validate and parse date value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                self._add_error(row, field, f'{field} is required')
            return None
        
        # Already a date
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        
        # datetime to date
        if isinstance(value, datetime):
            return value.date()
        
        # Parse string
        value = str(value).strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        
        self._add_error(row, field, f'Could not parse date: {value}', value)
        return None
    
    def _validate_enum(self, value: Any, field: str, valid_values: set,
                       row: int, default: Optional[str] = None) -> Optional[str]:
        """Validate enum value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        
        value = str(value).strip().lower().replace(' ', '_').replace('-', '_')
        
        if value in valid_values:
            return value
        
        # Try fuzzy matching
        for valid in valid_values:
            if value in valid or valid in value:
                self._add_warning(row, field, f"Mapped '{value}' to '{valid}'", value)
                return valid
        
        if default:
            self._add_warning(row, field, f"Invalid value '{value}', using default '{default}'", value)
            return default
        
        self._add_error(row, field, f"Invalid value '{value}'. Valid: {', '.join(valid_values)}", value)
        return None
    
    def _validate_integer(self, value: Any, field: str, row: int,
                          min_val: Optional[int] = None, max_val: Optional[int] = None,
                          default: Optional[int] = None) -> Optional[int]:
        """Validate integer value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        
        try:
            if isinstance(value, float):
                int_val = int(value)
                if value != int_val:
                    self._add_warning(row, field, f"Truncated decimal value {value} to {int_val}")
            else:
                int_val = int(str(value).strip().replace(',', ''))
        except (ValueError, TypeError):
            self._add_error(row, field, f"Could not parse as integer: {value}", value)
            return default
        
        if min_val is not None and int_val < min_val:
            self._add_error(row, field, f"Value {int_val} below minimum {min_val}", value)
            return default
        
        if max_val is not None and int_val > max_val:
            self._add_error(row, field, f"Value {int_val} above maximum {max_val}", value)
            return default
        
        return int_val
    
    def _validate_float(self, value: Any, field: str, row: int,
                        min_val: Optional[float] = None, max_val: Optional[float] = None,
                        default: Optional[float] = None) -> Optional[float]:
        """Validate float value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        
        try:
            # Handle currency formatting
            str_val = str(value).strip().replace(',', '').replace('$', '').replace('€', '').replace('£', '')
            float_val = float(str_val)
        except (ValueError, TypeError):
            self._add_error(row, field, f"Could not parse as number: {value}", value)
            return default
        
        if min_val is not None and float_val < min_val:
            self._add_error(row, field, f"Value {float_val} below minimum {min_val}", value)
            return default
        
        if max_val is not None and float_val > max_val:
            self._add_error(row, field, f"Value {float_val} above maximum {max_val}", value)
            return default
        
        return float_val
    
    def _validate_boolean(self, value: Any, field: str, row: int,
                          default: bool = False) -> bool:
        """Validate boolean value."""
        if value is None:
            return default
        
        if isinstance(value, bool):
            return value
        
        str_val = str(value).strip().lower()
        
        if str_val in ('true', 'yes', 'y', '1', 'on', 'x'):
            return True
        if str_val in ('false', 'no', 'n', '0', 'off', ''):
            return False
        
        self._add_warning(row, field, f"Could not parse '{value}' as boolean, using {default}", value)
        return default
    
    def _validate_string(self, value: Any, field: str, row: int,
                         required: bool = False, max_length: Optional[int] = None) -> Optional[str]:
        """Validate string value."""
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                self._add_error(row, field, f'{field} is required')
            return None
        
        str_val = str(value).strip()
        
        if max_length and len(str_val) > max_length:
            self._add_warning(row, field, f"Truncated from {len(str_val)} to {max_length} chars")
            str_val = str_val[:max_length]
        
        return str_val
    
    def _validate_email(self, value: Any, field: str, row: int) -> Optional[str]:
        """Validate email format."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        email = str(value).strip().lower()
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            self._add_error(row, field, f"Invalid email format: {email}", value)
            return None
        
        return email
    
    def _validate_url(self, value: Any, field: str, row: int) -> Optional[str]:
        """Validate URL format."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        url = str(value).strip()
        
        # Add https if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Basic URL pattern
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*$'
        if not re.match(pattern, url):
            self._add_error(row, field, f"Invalid URL format: {url}", value)
            return None
        
        if len(url) > 500:
            self._add_warning(row, field, f"URL truncated to 500 characters")
            url = url[:500]
        
        return url
    
    def _validate_date_logic(self, data: Dict[str, Any], row: int) -> None:
        """Validate date logic across fields."""
        submission = data.get('submission_date')
        due = data.get('due_date')
        completion = data.get('completion_date')
        
        if submission and due and due < submission:
            self._add_error(row, 'due_date', 'Due date cannot be before submission date')
        
        if submission and completion and completion < submission:
            self._add_error(row, 'completion_date', 'Completion date cannot be before submission date')
    
    def _validate_page_logic(self, data: Dict[str, Any], row: int) -> None:
        """Validate page count logic."""
        processed = data.get('pages_processed')
        disclosed = data.get('pages_disclosed')
        
        if processed is not None and disclosed is not None:
            if disclosed > processed:
                self._add_warning(
                    row, 'pages_disclosed', 
                    f'Pages disclosed ({disclosed}) exceeds pages processed ({processed})'
                )
    
    def _add_error(self, row: int, field: str, message: str, value: Any = None) -> None:
        """Add an error."""
        self.errors.append(RecordError(
            row_number=row,
            field_name=field,
            error_message=message,
            severity=ErrorSeverity.ERROR,
            raw_value=value
        ))
    
    def _add_warning(self, row: int, field: str, message: str, value: Any = None) -> None:
        """Add a warning."""
        error = RecordError(
            row_number=row,
            field_name=field,
            error_message=message,
            severity=ErrorSeverity.WARNING,
            raw_value=value
        )
        if self.strict_mode:
            self.errors.append(error)
        else:
            self.warnings.append(error)
