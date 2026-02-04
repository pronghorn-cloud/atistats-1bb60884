"""Data transformation and normalization for ATI request ingestion."""

from typing import Any, Dict, List, Optional, Callable
from datetime import date, timedelta
import re


class DataTransformer:
    """Transforms and normalizes data for ingestion."""
    
    # Standard field mappings (source column -> target field)
    ATI_REQUEST_FIELD_MAPPINGS: Dict[str, str] = {
        # Request number variations
        'request_number': 'request_number',
        'request_no': 'request_number',
        'request_id': 'request_number',
        'reference_number': 'request_number',
        'ref_no': 'request_number',
        'ref': 'request_number',
        'file_number': 'request_number',
        
        # Public body variations
        'public_body_id': 'public_body_id',
        'public_body_name': 'public_body_name',
        'public_body': 'public_body_name',
        'organization': 'public_body_name',
        'org': 'public_body_name',
        'department': 'public_body_name',
        'agency': 'public_body_name',
        'institution': 'public_body_name',
        
        # Date variations
        'submission_date': 'submission_date',
        'date_received': 'submission_date',
        'received_date': 'submission_date',
        'date_submitted': 'submission_date',
        'filed_date': 'submission_date',
        'request_date': 'submission_date',
        
        'due_date': 'due_date',
        'deadline': 'due_date',
        'statutory_deadline': 'due_date',
        'response_due': 'due_date',
        
        'completion_date': 'completion_date',
        'date_completed': 'completion_date',
        'completed_date': 'completion_date',
        'closed_date': 'completion_date',
        'date_closed': 'completion_date',
        'response_date': 'completion_date',
        
        # Type variations
        'request_type': 'request_type',
        'type': 'request_type',
        'category': 'request_type',
        
        # Status variations
        'status': 'status',
        'request_status': 'status',
        'current_status': 'status',
        'state': 'status',
        
        # Outcome variations
        'outcome': 'outcome',
        'disposition': 'outcome',
        'result': 'outcome',
        'decision': 'outcome',
        
        # Extension variations
        'extension_days': 'extension_days',
        'extension': 'extension_days',
        'days_extended': 'extension_days',
        'ext_days': 'extension_days',
        
        # Page count variations
        'pages_processed': 'pages_processed',
        'pages_reviewed': 'pages_processed',
        'total_pages': 'pages_processed',
        
        'pages_disclosed': 'pages_disclosed',
        'pages_released': 'pages_disclosed',
        'disclosed_pages': 'pages_disclosed',
        
        # Fee variations
        'fees_charged': 'fees_charged',
        'fees': 'fees_charged',
        'fee': 'fees_charged',
        'amount_charged': 'fees_charged',
        'cost': 'fees_charged',
        
        # Boolean variations
        'is_deemed_refusal': 'is_deemed_refusal',
        'deemed_refusal': 'is_deemed_refusal',
        'overdue': 'is_deemed_refusal',
        
        # Description variations
        'summary': 'summary',
        'description': 'summary',
        'request_summary': 'summary',
        'subject': 'summary',
        'topic': 'summary',
    }
    
    PUBLIC_BODY_FIELD_MAPPINGS: Dict[str, str] = {
        'name': 'name',
        'organization_name': 'name',
        'org_name': 'name',
        'public_body_name': 'name',
        'department_name': 'name',
        
        'abbreviation': 'abbreviation',
        'abbr': 'abbreviation',
        'short_name': 'abbreviation',
        'acronym': 'abbreviation',
        
        'description': 'description',
        'mandate': 'description',
        'about': 'description',
        
        'contact_email': 'contact_email',
        'email': 'contact_email',
        'ati_email': 'contact_email',
        
        'website_url': 'website_url',
        'website': 'website_url',
        'url': 'website_url',
        
        'is_active': 'is_active',
        'active': 'is_active',
    }
    
    # Status value mappings for normalization
    STATUS_MAPPINGS: Dict[str, str] = {
        'received': 'received',
        'new': 'received',
        'open': 'received',
        'opened': 'received',
        
        'in_progress': 'in_progress',
        'in progress': 'in_progress',
        'processing': 'in_progress',
        'active': 'in_progress',
        'ongoing': 'in_progress',
        'underway': 'in_progress',
        
        'pending_clarification': 'pending_clarification',
        'pending clarification': 'pending_clarification',
        'awaiting_clarification': 'pending_clarification',
        'clarification_needed': 'pending_clarification',
        
        'extended': 'extended',
        'extension': 'extended',
        'time_extended': 'extended',
        
        'completed': 'completed',
        'complete': 'completed',
        'closed': 'completed',
        'done': 'completed',
        'finished': 'completed',
        'resolved': 'completed',
        
        'abandoned': 'abandoned',
        'inactive': 'abandoned',
        'expired': 'abandoned',
        
        'transferred': 'transferred',
        'transfer': 'transferred',
        'referred': 'transferred',
    }
    
    # Outcome value mappings
    OUTCOME_MAPPINGS: Dict[str, str] = {
        'full_disclosure': 'full_disclosure',
        'full disclosure': 'full_disclosure',
        'fully_disclosed': 'full_disclosure',
        'all_disclosed': 'full_disclosure',
        'complete_disclosure': 'full_disclosure',
        
        'partial_disclosure': 'partial_disclosure',
        'partial disclosure': 'partial_disclosure',
        'partially_disclosed': 'partial_disclosure',
        'partial': 'partial_disclosure',
        
        'no_disclosure': 'no_disclosure',
        'no disclosure': 'no_disclosure',
        'none_disclosed': 'no_disclosure',
        'denied': 'no_disclosure',
        'refused': 'no_disclosure',
        'exemption': 'no_disclosure',
        
        'no_records_exist': 'no_records_exist',
        'no records exist': 'no_records_exist',
        'no_records': 'no_records_exist',
        'not_found': 'no_records_exist',
        'no records': 'no_records_exist',
        
        'transferred': 'transferred',
        'transfer': 'transferred',
        'referred': 'transferred',
        
        'abandoned': 'abandoned',
        'inactive': 'abandoned',
        
        'withdrawn': 'withdrawn',
        'withdraw': 'withdrawn',
        'cancelled': 'withdrawn',
        'canceled': 'withdrawn',
        
        'pending': 'pending',
        'in_progress': 'pending',
        'ongoing': 'pending',
        'open': 'pending',
    }
    
    # Request type mappings
    TYPE_MAPPINGS: Dict[str, str] = {
        'personal': 'personal',
        'personal_information': 'personal',
        'privacy': 'personal',
        
        'non_personal': 'non_personal',
        'non-personal': 'non_personal',
        'nonpersonal': 'non_personal',
        'access': 'non_personal',
        'ati': 'non_personal',
        'foi': 'non_personal',
        'foia': 'non_personal',
        'general': 'non_personal',
        
        'mixed': 'mixed',
        'combined': 'mixed',
        'both': 'mixed',
        
        'correction': 'correction',
        'correct': 'correction',
        'amendment': 'correction',
        'amend': 'correction',
    }
    
    def __init__(self, custom_field_mappings: Optional[Dict[str, str]] = None):
        """Initialize transformer with optional custom mappings.
        
        Args:
            custom_field_mappings: Additional field name mappings to use
        """
        self.field_mappings = self.ATI_REQUEST_FIELD_MAPPINGS.copy()
        if custom_field_mappings:
            self.field_mappings.update(custom_field_mappings)
    
    def normalize_column_name(self, column: str) -> str:
        """Normalize a column name for matching.
        
        Args:
            column: Raw column name from source data
            
        Returns:
            Normalized column name
        """
        # Lowercase, strip, replace spaces and special chars with underscores
        normalized = column.lower().strip()
        normalized = re.sub(r'[\s\-\.]+', '_', normalized)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        return normalized.strip('_')
    
    def map_columns(self, data: Dict[str, Any], 
                    field_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Map source columns to target field names.
        
        Args:
            data: Source data dictionary
            field_mappings: Field mappings to use (defaults to ATI request mappings)
            
        Returns:
            Dictionary with mapped field names
        """
        mappings = field_mappings or self.field_mappings
        result = {}
        
        for source_col, value in data.items():
            normalized = self.normalize_column_name(source_col)
            target_field = mappings.get(normalized)
            
            if target_field:
                # Don't overwrite if we already have a value
                if target_field not in result or result[target_field] is None:
                    result[target_field] = value
            else:
                # Keep unmapped fields with normalized names
                result[normalized] = value
        
        return result
    
    def transform_ati_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw ATI request data.
        
        Args:
            data: Raw source data
            
        Returns:
            Transformed data ready for validation
        """
        # First map columns to standard names
        mapped = self.map_columns(data, self.ATI_REQUEST_FIELD_MAPPINGS)
        
        # Normalize enum values
        if 'status' in mapped and mapped['status']:
            mapped['status'] = self._normalize_enum_value(
                mapped['status'], self.STATUS_MAPPINGS
            )
        
        if 'outcome' in mapped and mapped['outcome']:
            mapped['outcome'] = self._normalize_enum_value(
                mapped['outcome'], self.OUTCOME_MAPPINGS
            )
        
        if 'request_type' in mapped and mapped['request_type']:
            mapped['request_type'] = self._normalize_enum_value(
                mapped['request_type'], self.TYPE_MAPPINGS
            )
        
        # Calculate due date if not provided but we have submission date
        if not mapped.get('due_date') and mapped.get('submission_date'):
            mapped['due_date'] = self._calculate_default_due_date(mapped['submission_date'])
        
        return mapped
    
    def transform_public_body(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw public body data.
        
        Args:
            data: Raw source data
            
        Returns:
            Transformed data ready for validation
        """
        return self.map_columns(data, self.PUBLIC_BODY_FIELD_MAPPINGS)
    
    def _normalize_enum_value(self, value: Any, mappings: Dict[str, str]) -> str:
        """Normalize an enum value using provided mappings."""
        if value is None:
            return value
        
        normalized = str(value).lower().strip()
        normalized = re.sub(r'[\s\-]+', '_', normalized)
        
        return mappings.get(normalized, normalized)
    
    def _calculate_default_due_date(self, submission_date: Any) -> Any:
        """Calculate default due date (30 days from submission)."""
        if isinstance(submission_date, date):
            return submission_date + timedelta(days=30)
        return None
    
    def batch_transform(
        self, 
        records: List[Dict[str, Any]], 
        transform_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform a batch of records.
        
        Args:
            records: List of raw records
            transform_func: Transformation function to apply
            
        Returns:
            List of transformed records
        """
        return [transform_func(record) for record in records]
