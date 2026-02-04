"""Unit tests for data transformers."""

import pytest
from datetime import date, timedelta

from src.services.ingestion.transformers import DataTransformer


class TestDataTransformerColumnMapping:
    """Test column name mapping functionality."""
    
    @pytest.fixture
    def transformer(self):
        return DataTransformer()
    
    def test_normalize_column_name_lowercase(self, transformer):
        """Test that column names are lowercased."""
        assert transformer.normalize_column_name('REQUEST_NUMBER') == 'request_number'
        assert transformer.normalize_column_name('PublicBody') == 'publicbody'
    
    def test_normalize_column_name_spaces_to_underscore(self, transformer):
        """Test that spaces become underscores."""
        assert transformer.normalize_column_name('Request Number') == 'request_number'
        assert transformer.normalize_column_name('Public  Body') == 'public_body'
    
    def test_normalize_column_name_special_chars(self, transformer):
        """Test removal of special characters."""
        assert transformer.normalize_column_name('Request-Number') == 'request_number'
        assert transformer.normalize_column_name('Request.Number') == 'request_number'
        assert transformer.normalize_column_name('Request (Number)') == 'request_number'
    
    def test_normalize_column_strips_whitespace(self, transformer):
        """Test that leading/trailing whitespace is removed."""
        assert transformer.normalize_column_name('  name  ') == 'name'
    
    def test_map_standard_columns(self, transformer):
        """Test mapping of standard column names."""
        data = {
            'request_number': 'ATI-001',
            'submission_date': '2024-01-15',
        }
        result = transformer.map_columns(data, transformer.ATI_REQUEST_FIELD_MAPPINGS)
        
        assert result['request_number'] == 'ATI-001'
        assert result['submission_date'] == '2024-01-15'
    
    def test_map_alternate_column_names(self, transformer):
        """Test mapping of alternate column names to standard names."""
        data = {
            'ref_no': 'ATI-001',  # Should map to request_number
            'date_received': '2024-01-15',  # Should map to submission_date
            'organization': 'TBS',  # Should map to public_body_name
        }
        result = transformer.map_columns(data, transformer.ATI_REQUEST_FIELD_MAPPINGS)
        
        assert result['request_number'] == 'ATI-001'
        assert result['submission_date'] == '2024-01-15'
        assert result['public_body_name'] == 'TBS'
    
    def test_preserve_unmapped_columns(self, transformer):
        """Test that unmapped columns are preserved with normalized names."""
        data = {
            'request_number': 'ATI-001',
            'custom_field': 'custom_value',
        }
        result = transformer.map_columns(data, transformer.ATI_REQUEST_FIELD_MAPPINGS)
        
        assert result['request_number'] == 'ATI-001'
        assert result['custom_field'] == 'custom_value'
    
    def test_first_value_wins(self, transformer):
        """Test that first mapped value is not overwritten."""
        data = {
            'request_number': 'ATI-001',
            'ref_no': 'REF-002',  # Also maps to request_number
        }
        result = transformer.map_columns(data, transformer.ATI_REQUEST_FIELD_MAPPINGS)
        
        # First value should be kept
        assert result['request_number'] == 'ATI-001'


class TestDataTransformerATIRequest:
    """Test ATI request transformation."""
    
    @pytest.fixture
    def transformer(self):
        return DataTransformer()
    
    def test_transform_basic_ati_request(self, transformer):
        """Test basic ATI request transformation."""
        data = {
            'request_number': 'ATI-001',
            'submission_date': '2024-01-15',
            'due_date': '2024-02-14',
            'status': 'received',
        }
        result = transformer.transform_ati_request(data)
        
        assert result['request_number'] == 'ATI-001'
        assert result['status'] == 'received'
    
    def test_normalize_status_values(self, transformer):
        """Test normalization of status values."""
        test_cases = [
            ('received', 'received'),
            ('new', 'received'),
            ('in progress', 'in_progress'),
            ('processing', 'in_progress'),
            ('complete', 'completed'),
            ('closed', 'completed'),
        ]
        
        for input_status, expected in test_cases:
            data = {'status': input_status}
            result = transformer.transform_ati_request(data)
            assert result['status'] == expected, f"Expected {expected} for {input_status}"
    
    def test_normalize_outcome_values(self, transformer):
        """Test normalization of outcome values."""
        test_cases = [
            ('full disclosure', 'full_disclosure'),
            ('fully_disclosed', 'full_disclosure'),
            ('partial', 'partial_disclosure'),
            ('denied', 'no_disclosure'),
            ('no records', 'no_records_exist'),
        ]
        
        for input_outcome, expected in test_cases:
            data = {'outcome': input_outcome}
            result = transformer.transform_ati_request(data)
            assert result['outcome'] == expected, f"Expected {expected} for {input_outcome}"
    
    def test_normalize_request_type_values(self, transformer):
        """Test normalization of request type values."""
        test_cases = [
            ('personal', 'personal'),
            ('privacy', 'personal'),
            ('non-personal', 'non_personal'),
            ('foi', 'non_personal'),
            ('foia', 'non_personal'),
            ('mixed', 'mixed'),
            ('correction', 'correction'),
        ]
        
        for input_type, expected in test_cases:
            data = {'request_type': input_type}
            result = transformer.transform_ati_request(data)
            assert result['request_type'] == expected, f"Expected {expected} for {input_type}"
    
    def test_calculate_default_due_date(self, transformer):
        """Test automatic due date calculation."""
        submission = date(2024, 1, 15)
        data = {
            'request_number': 'ATI-001',
            'submission_date': submission,
        }
        result = transformer.transform_ati_request(data)
        
        # Default is 30 days from submission
        expected_due = submission + timedelta(days=30)
        assert result['due_date'] == expected_due
    
    def test_no_default_due_date_if_provided(self, transformer):
        """Test that explicit due date is preserved."""
        data = {
            'request_number': 'ATI-001',
            'submission_date': date(2024, 1, 15),
            'due_date': date(2024, 3, 15),  # Custom due date
        }
        result = transformer.transform_ati_request(data)
        
        assert result['due_date'] == date(2024, 3, 15)


class TestDataTransformerPublicBody:
    """Test public body transformation."""
    
    @pytest.fixture
    def transformer(self):
        return DataTransformer()
    
    def test_transform_basic_public_body(self, transformer):
        """Test basic public body transformation."""
        data = {
            'name': 'Treasury Board Secretariat',
            'abbreviation': 'TBS',
        }
        result = transformer.transform_public_body(data)
        
        assert result['name'] == 'Treasury Board Secretariat'
        assert result['abbreviation'] == 'TBS'
    
    def test_map_alternate_public_body_columns(self, transformer):
        """Test mapping alternate column names for public bodies."""
        data = {
            'organization_name': 'Treasury Board Secretariat',
            'acronym': 'TBS',
            'email': 'ati@tbs.gc.ca',
            'website': 'https://www.canada.ca',
        }
        result = transformer.transform_public_body(data)
        
        assert result['name'] == 'Treasury Board Secretariat'
        assert result['abbreviation'] == 'TBS'
        assert result['contact_email'] == 'ati@tbs.gc.ca'
        assert result['website_url'] == 'https://www.canada.ca'


class TestDataTransformerCustomMappings:
    """Test custom field mapping functionality."""
    
    def test_custom_mappings_added(self):
        """Test that custom mappings are added to default mappings."""
        custom = {'my_custom_field': 'request_number'}
        transformer = DataTransformer(custom_field_mappings=custom)
        
        data = {'my_custom_field': 'ATI-001'}
        result = transformer.map_columns(data)
        
        assert result['request_number'] == 'ATI-001'
    
    def test_custom_mappings_override_defaults(self):
        """Test that custom mappings can override defaults."""
        custom = {'ref': 'summary'}  # Override default mapping
        transformer = DataTransformer(custom_field_mappings=custom)
        
        data = {'ref': 'My summary text'}
        result = transformer.map_columns(data)
        
        assert result['summary'] == 'My summary text'


class TestDataTransformerBatchOperations:
    """Test batch transformation operations."""
    
    @pytest.fixture
    def transformer(self):
        return DataTransformer()
    
    def test_batch_transform(self, transformer):
        """Test batch transformation of multiple records."""
        records = [
            {'request_number': 'ATI-001', 'status': 'new'},
            {'request_number': 'ATI-002', 'status': 'complete'},
            {'request_number': 'ATI-003', 'status': 'processing'},
        ]
        
        results = transformer.batch_transform(records, transformer.transform_ati_request)
        
        assert len(results) == 3
        assert results[0]['status'] == 'received'
        assert results[1]['status'] == 'completed'
        assert results[2]['status'] == 'in_progress'
