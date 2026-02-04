"""Integration tests for ATI Requests API endpoints."""

import pytest
from uuid import uuid4
from datetime import date


class TestATIRequestsAPI:
    """Test ATI Requests CRUD API endpoints."""
    
    def test_list_ati_requests(self, client, api_v1_prefix):
        """Test GET /api/v1/ati-requests returns list."""
        response = client.get(f"{api_v1_prefix}/ati-requests")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or 'items' in data
    
    def test_list_ati_requests_with_pagination(self, client, api_v1_prefix):
        """Test pagination parameters."""
        response = client.get(
            f"{api_v1_prefix}/ati-requests",
            params={'skip': 0, 'limit': 10}
        )
        
        assert response.status_code == 200
    
    def test_list_ati_requests_filter_by_status(self, client, api_v1_prefix):
        """Test filtering by status."""
        response = client.get(
            f"{api_v1_prefix}/ati-requests",
            params={'status': 'received'}
        )
        
        assert response.status_code == 200
    
    def test_list_ati_requests_filter_by_outcome(self, client, api_v1_prefix):
        """Test filtering by outcome."""
        response = client.get(
            f"{api_v1_prefix}/ati-requests",
            params={'outcome': 'pending'}
        )
        
        assert response.status_code == 200
    
    def test_list_ati_requests_filter_by_public_body(self, client, api_v1_prefix):
        """Test filtering by public body ID."""
        fake_id = uuid4()
        response = client.get(
            f"{api_v1_prefix}/ati-requests",
            params={'public_body_id': str(fake_id)}
        )
        
        assert response.status_code == 200
    
    def test_get_nonexistent_ati_request(self, client, api_v1_prefix):
        """Test GET with non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.get(f"{api_v1_prefix}/ati-requests/{fake_id}")
        
        assert response.status_code == 404
    
    def test_get_invalid_uuid(self, client, api_v1_prefix):
        """Test GET with invalid UUID returns 422."""
        response = client.get(f"{api_v1_prefix}/ati-requests/not-a-uuid")
        
        assert response.status_code == 422
    
    def test_get_by_request_number_not_found(self, client, api_v1_prefix):
        """Test GET by request number when not found."""
        response = client.get(
            f"{api_v1_prefix}/ati-requests/by-number/NONEXISTENT-001"
        )
        
        assert response.status_code == 404


class TestATIRequestsStatistics:
    """Test ATI Requests statistics endpoint."""
    
    def test_get_statistics(self, client, api_v1_prefix):
        """Test GET /api/v1/ati-requests/statistics."""
        response = client.get(f"{api_v1_prefix}/ati-requests/statistics")
        
        assert response.status_code == 200
        data = response.json()
        # Should return some statistics structure
        assert isinstance(data, dict)
    
    def test_get_statistics_filtered(self, client, api_v1_prefix):
        """Test statistics with filters."""
        fake_id = uuid4()
        response = client.get(
            f"{api_v1_prefix}/ati-requests/statistics",
            params={'public_body_id': str(fake_id)}
        )
        
        assert response.status_code == 200


class TestATIRequestsOverdue:
    """Test ATI Requests overdue endpoint."""
    
    def test_get_overdue_requests(self, client, api_v1_prefix):
        """Test GET /api/v1/ati-requests/overdue."""
        response = client.get(f"{api_v1_prefix}/ati-requests/overdue")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or 'items' in data


class TestATIRequestsCreate:
    """Test ATI Requests creation endpoint."""
    
    def test_create_validation_error(self, client, api_v1_prefix):
        """Test that creating without required fields returns 422."""
        response = client.post(
            f"{api_v1_prefix}/ati-requests",
            json={'summary': 'Test'}  # Missing required fields
        )
        
        assert response.status_code == 422
        assert 'detail' in response.json()
    
    def test_create_invalid_date_format(self, client, api_v1_prefix):
        """Test that invalid date format returns 422."""
        response = client.post(
            f"{api_v1_prefix}/ati-requests",
            json={
                'request_number': 'TEST-001',
                'public_body_id': str(uuid4()),
                'submission_date': 'not-a-date',
                'due_date': '2024-02-14',
            }
        )
        
        assert response.status_code == 422
    
    def test_create_invalid_enum(self, client, api_v1_prefix):
        """Test that invalid enum value returns 422."""
        response = client.post(
            f"{api_v1_prefix}/ati-requests",
            json={
                'request_number': 'TEST-001',
                'public_body_id': str(uuid4()),
                'submission_date': '2024-01-15',
                'due_date': '2024-02-14',
                'status': 'invalid_status',
            }
        )
        
        assert response.status_code == 422


class TestATIRequestsUpdate:
    """Test ATI Requests update endpoint."""
    
    def test_update_nonexistent_returns_404(self, client, api_v1_prefix):
        """Test PATCH on non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.patch(
            f"{api_v1_prefix}/ati-requests/{fake_id}",
            json={'summary': 'Updated summary'}
        )
        
        assert response.status_code == 404


class TestATIRequestsDelete:
    """Test ATI Requests delete endpoint."""
    
    def test_delete_nonexistent_returns_404(self, client, api_v1_prefix):
        """Test DELETE on non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.delete(f"{api_v1_prefix}/ati-requests/{fake_id}")
        
        assert response.status_code == 404
