"""Unit tests for data validators."""

import pytest
from datetime import date, datetime

from src.services.ingestion.validators import DataValidator, ValidationError
from src.services.ingestion.result import ErrorSeverity


class TestDataValidatorATIRequest:
    """Test ATI request validation."""
    
    @pytest.fixture
    def validator(self):
        """Create a DataValidator instance."""
        return DataValidator()
    
    @pytest.fixture
    def valid_ati_data(self):
        """Create valid ATI request data."""
        return {
            'request_number': 'ATI-2024-001',
            'submission_date': '2024-01-15',
            'due_date': '2024-02-14',
            'public_body_name': 'Treasury Board Secretariat',
            'request_type': 'non_personal',
            'status': 'received',
            'outcome': 'pending',
        }
    
    def test_validate_valid_ati_request(self, validator, valid_ati_data):
        """Test validation of a valid ATI request."""
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['request_number'] == 'ATI-2024-001'
        assert cleaned['public_body_name'] == 'Treasury Board Secretariat'
    
    def test_missing_request_number(self, validator, valid_ati_data):
        """Test that missing request_number causes error."""
        del valid_ati_data['request_number']
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'request_number' for e in validator.errors)
    
    def test_missing_public_body(self, validator, valid_ati_data):
        """Test that missing public body info causes error."""
        del valid_ati_data['public_body_name']
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'public_body' for e in validator.errors)
    
    def test_public_body_id_instead_of_name(self, validator, valid_ati_data):
        """Test that public_body_id can be used instead of name."""
        del valid_ati_data['public_body_name']
        valid_ati_data['public_body_id'] = '550e8400-e29b-41d4-a716-446655440000'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['public_body_id'] == '550e8400-e29b-41d4-a716-446655440000'
    
    def test_date_parsing_iso_format(self, validator, valid_ati_data):
        """Test parsing ISO format dates."""
        valid_ati_data['submission_date'] = '2024-01-15'
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['submission_date'] == date(2024, 1, 15)
    
    def test_date_parsing_slash_format(self, validator, valid_ati_data):
        """Test parsing slash format dates."""
        valid_ati_data['submission_date'] = '15/01/2024'
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['submission_date'] == date(2024, 1, 15)
    
    def test_date_parsing_datetime_object(self, validator, valid_ati_data):
        """Test handling datetime objects."""
        valid_ati_data['submission_date'] = datetime(2024, 1, 15, 10, 30, 0)
        valid_ati_data['due_date'] = date(2024, 2, 14)
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['submission_date'] == date(2024, 1, 15)
    
    def test_invalid_date_format(self, validator, valid_ati_data):
        """Test that invalid dates cause errors."""
        valid_ati_data['submission_date'] = 'not-a-date'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'submission_date' for e in validator.errors)
    
    def test_due_date_before_submission_date(self, validator, valid_ati_data):
        """Test that due_date before submission_date is invalid."""
        valid_ati_data['submission_date'] = '2024-02-15'
        valid_ati_data['due_date'] = '2024-01-15'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'due_date' for e in validator.errors)
    
    def test_valid_enum_status(self, validator, valid_ati_data):
        """Test valid status enum values."""
        for status in ['received', 'in_progress', 'completed', 'abandoned']:
            valid_ati_data['status'] = status
            is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
            
            assert is_valid is True
            assert cleaned['status'] == status
    
    def test_invalid_enum_with_default(self, validator, valid_ati_data):
        """Test that invalid enum values get default."""
        valid_ati_data['status'] = 'invalid_status_value'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        # Should have a warning but still be valid with default
        assert is_valid is True
        assert cleaned['status'] == 'received'  # default value
        assert len(validator.warnings) > 0
    
    def test_fuzzy_enum_matching(self, validator, valid_ati_data):
        """Test fuzzy matching of enum values."""
        valid_ati_data['outcome'] = 'partial'  # Should match 'partial_disclosure'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['outcome'] == 'partial_disclosure'
    
    def test_integer_field_validation(self, validator, valid_ati_data):
        """Test integer field validation."""
        valid_ati_data['pages_processed'] = '100'
        valid_ati_data['extension_days'] = 30
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['pages_processed'] == 100
        assert cleaned['extension_days'] == 30
    
    def test_negative_integer_error(self, validator, valid_ati_data):
        """Test that negative page counts are rejected."""
        valid_ati_data['pages_processed'] = '-10'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'pages_processed' for e in validator.errors)
    
    def test_float_field_validation(self, validator, valid_ati_data):
        """Test float field validation."""
        valid_ati_data['fees_charged'] = '$25.50'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['fees_charged'] == 25.50
    
    def test_boolean_field_validation(self, validator, valid_ati_data):
        """Test boolean field validation."""
        test_cases = [
            ('true', True),
            ('yes', True),
            ('1', True),
            ('false', False),
            ('no', False),
            ('0', False),
        ]
        
        for input_val, expected in test_cases:
            valid_ati_data['is_deemed_refusal'] = input_val
            is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
            
            assert is_valid is True
            assert cleaned['is_deemed_refusal'] == expected
    
    def test_page_logic_warning(self, validator, valid_ati_data):
        """Test warning when pages_disclosed > pages_processed."""
        valid_ati_data['pages_processed'] = '100'
        valid_ati_data['pages_disclosed'] = '150'
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        # Should be valid but with warning
        assert is_valid is True
        assert any('pages_disclosed' in w.field_name for w in validator.warnings)
    
    def test_strict_mode_warnings_become_errors(self, valid_ati_data):
        """Test that warnings become errors in strict mode."""
        validator = DataValidator(strict_mode=True)
        valid_ati_data['status'] = 'invalid_status'  # Would normally be warning
        
        is_valid, cleaned = validator.validate_ati_request(valid_ati_data, row_number=1)
        
        assert is_valid is False
        assert len(validator.errors) > 0


class TestDataValidatorPublicBody:
    """Test public body validation."""
    
    @pytest.fixture
    def validator(self):
        return DataValidator()
    
    @pytest.fixture
    def valid_public_body_data(self):
        return {
            'name': 'Treasury Board Secretariat',
            'abbreviation': 'TBS',
            'description': 'Central agency of the Government of Canada',
            'contact_email': 'ati@tbs-sct.gc.ca',
            'website_url': 'https://www.canada.ca/en/treasury-board-secretariat.html',
            'is_active': True,
        }
    
    def test_validate_valid_public_body(self, validator, valid_public_body_data):
        """Test validation of a valid public body."""
        is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['name'] == 'Treasury Board Secretariat'
        assert cleaned['abbreviation'] == 'TBS'
    
    def test_missing_name(self, validator, valid_public_body_data):
        """Test that missing name causes error."""
        del valid_public_body_data['name']
        
        is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'name' for e in validator.errors)
    
    def test_invalid_email_format(self, validator, valid_public_body_data):
        """Test that invalid email format is rejected."""
        valid_public_body_data['contact_email'] = 'not-an-email'
        
        is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'contact_email' for e in validator.errors)
    
    def test_valid_email_formats(self, validator, valid_public_body_data):
        """Test various valid email formats."""
        valid_emails = [
            'test@example.com',
            'test.user@example.co.uk',
            'test+filter@example.org',
        ]
        
        for email in valid_emails:
            valid_public_body_data['contact_email'] = email
            is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
            
            assert is_valid is True
            assert cleaned['contact_email'] == email.lower()
    
    def test_url_validation_auto_https(self, validator, valid_public_body_data):
        """Test that URLs without protocol get https:// added."""
        valid_public_body_data['website_url'] = 'www.example.com'
        
        is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
        
        assert is_valid is True
        assert cleaned['website_url'] == 'https://www.example.com'
    
    def test_invalid_url_format(self, validator, valid_public_body_data):
        """Test that invalid URLs are rejected."""
        valid_public_body_data['website_url'] = 'not a url at all'
        
        is_valid, cleaned = validator.validate_public_body(valid_public_body_data, row_number=1)
        
        assert is_valid is False
        assert any(e.field_name == 'website_url' for e in validator.errors)


class TestValidatorErrorSeverity:
    """Test error severity handling."""
    
    def test_errors_have_correct_severity(self):
        """Test that errors are marked with ERROR severity."""
        validator = DataValidator()
        data = {'request_number': None}  # Missing required field
        
        validator.validate_ati_request(data, row_number=1)
        
        assert all(e.severity == ErrorSeverity.ERROR for e in validator.errors)
    
    def test_warnings_have_correct_severity(self):
        """Test that warnings are marked with WARNING severity."""
        validator = DataValidator()
        data = {
            'request_number': 'TEST-001',
            'submission_date': '2024-01-15',
            'due_date': '2024-02-14',
            'public_body_name': 'Test Body',
            'status': 'unknown_status',  # Will generate warning
        }
        
        validator.validate_ati_request(data, row_number=1)
        
        assert all(w.severity == ErrorSeverity.WARNING for w in validator.warnings)
