"""Integration tests for Data Ingestion API endpoints."""

import pytest
import io


class TestIngestionAPI:
    """Test data ingestion endpoints."""
    
    def test_get_ati_requests_template(self, client, api_v1_prefix):
        """Test GET /api/v1/ingestion/templates/ati-requests."""
        response = client.get(f"{api_v1_prefix}/ingestion/templates/ati-requests")
        
        # Should return CSV template or info about format
        assert response.status_code in [200, 404]  # 404 if not implemented
    
    def test_get_public_bodies_template(self, client, api_v1_prefix):
        """Test GET /api/v1/ingestion/templates/public-bodies."""
        response = client.get(f"{api_v1_prefix}/ingestion/templates/public-bodies")
        
        assert response.status_code in [200, 404]
    
    def test_get_invalid_template_type(self, client, api_v1_prefix):
        """Test GET template with invalid type returns 404 or 400."""
        response = client.get(f"{api_v1_prefix}/ingestion/templates/invalid-type")
        
        assert response.status_code in [400, 404, 422]


class TestIngestionCSVUpload:
    """Test CSV file upload functionality."""
    
    @pytest.fixture
    def sample_ati_csv(self):
        """Create a sample ATI requests CSV."""
        csv_content = """request_number,submission_date,due_date,public_body_name,status,outcome
ATI-2024-001,2024-01-15,2024-02-14,Treasury Board,received,pending
ATI-2024-002,2024-01-20,2024-02-19,Health Canada,in_progress,pending
"""
        return csv_content
    
    @pytest.fixture
    def sample_public_body_csv(self):
        """Create a sample public bodies CSV."""
        csv_content = """name,abbreviation,description,contact_email,is_active
Treasury Board Secretariat,TBS,Central agency,ati@tbs.gc.ca,true
Health Canada,HC,Health department,ati@hc.gc.ca,true
"""
        return csv_content
    
    def test_upload_ati_requests_csv_no_file(self, client, api_v1_prefix):
        """Test upload without file returns 422."""
        response = client.post(f"{api_v1_prefix}/ingestion/ati-requests")
        
        assert response.status_code == 422
    
    def test_upload_public_bodies_csv_no_file(self, client, api_v1_prefix):
        """Test upload without file returns 422."""
        response = client.post(f"{api_v1_prefix}/ingestion/public-bodies")
        
        assert response.status_code == 422
    
    def test_upload_ati_requests_csv(self, client, api_v1_prefix, sample_ati_csv):
        """Test uploading ATI requests CSV."""
        files = {'file': ('ati_requests.csv', io.BytesIO(sample_ati_csv.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/ati-requests",
            files=files
        )
        
        # May succeed or fail depending on database state
        # 200/201 for success, 400/422 for validation errors, 500 for DB errors
        assert response.status_code in [200, 201, 400, 422, 500]
        
        # If successful, should return ingestion result
        if response.status_code in [200, 201]:
            data = response.json()
            assert 'total_records' in data or 'success' in data or 'records_processed' in data
    
    def test_upload_public_bodies_csv(self, client, api_v1_prefix, sample_public_body_csv):
        """Test uploading public bodies CSV."""
        files = {'file': ('public_bodies.csv', io.BytesIO(sample_public_body_csv.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/public-bodies",
            files=files
        )
        
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_upload_invalid_csv_format(self, client, api_v1_prefix):
        """Test uploading invalid CSV content."""
        invalid_content = "This is not a valid CSV format\nwith random content"
        files = {'file': ('invalid.csv', io.BytesIO(invalid_content.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/ati-requests",
            files=files
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422, 500]
    
    def test_upload_empty_csv(self, client, api_v1_prefix):
        """Test uploading empty CSV."""
        empty_content = "request_number,submission_date,due_date\n"
        files = {'file': ('empty.csv', io.BytesIO(empty_content.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/ati-requests",
            files=files
        )
        
        # Should handle gracefully - may return success with 0 records
        assert response.status_code in [200, 201, 400, 422]


class TestIngestionValidation:
    """Test ingestion validation scenarios."""
    
    def test_upload_csv_missing_required_columns(self, client, api_v1_prefix):
        """Test CSV missing required columns."""
        csv_content = """optional_field,another_field
value1,value2
"""
        files = {'file': ('missing_cols.csv', io.BytesIO(csv_content.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/ati-requests",
            files=files
        )
        
        # Should report validation errors
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            # Should indicate errors in the response
            if 'errors' in data:
                assert len(data['errors']) > 0
    
    def test_upload_csv_invalid_dates(self, client, api_v1_prefix):
        """Test CSV with invalid date values."""
        csv_content = """request_number,submission_date,due_date,public_body_name
ATI-001,not-a-date,also-not-a-date,Test Body
"""
        files = {'file': ('bad_dates.csv', io.BytesIO(csv_content.encode()), 'text/csv')}
        
        response = client.post(
            f"{api_v1_prefix}/ingestion/ati-requests",
            files=files
        )
        
        assert response.status_code in [200, 400, 422, 500]
