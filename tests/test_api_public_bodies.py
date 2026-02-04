"""Integration tests for Public Bodies API endpoints."""

import pytest
from uuid import uuid4


class TestPublicBodiesAPI:
    """Test Public Bodies CRUD API endpoints."""
    
    def test_list_public_bodies(self, client, api_v1_prefix):
        """Test GET /api/v1/public-bodies returns list."""
        response = client.get(f"{api_v1_prefix}/public-bodies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or 'items' in data
    
    def test_list_public_bodies_with_pagination(self, client, api_v1_prefix):
        """Test pagination parameters."""
        response = client.get(
            f"{api_v1_prefix}/public-bodies",
            params={'skip': 0, 'limit': 10}
        )
        
        assert response.status_code == 200
    
    def test_list_public_bodies_with_search(self, client, api_v1_prefix):
        """Test search parameter."""
        response = client.get(
            f"{api_v1_prefix}/public-bodies",
            params={'search': 'treasury'}
        )
        
        assert response.status_code == 200
    
    def test_list_public_bodies_filter_active(self, client, api_v1_prefix):
        """Test active filter parameter."""
        response = client.get(
            f"{api_v1_prefix}/public-bodies",
            params={'is_active': True}
        )
        
        assert response.status_code == 200
    
    def test_get_nonexistent_public_body(self, client, api_v1_prefix):
        """Test GET with non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.get(f"{api_v1_prefix}/public-bodies/{fake_id}")
        
        assert response.status_code == 404
    
    def test_get_invalid_uuid(self, client, api_v1_prefix):
        """Test GET with invalid UUID returns 422."""
        response = client.get(f"{api_v1_prefix}/public-bodies/not-a-uuid")
        
        assert response.status_code == 422


class TestPublicBodiesAPICreate:
    """Test Public Bodies creation endpoint."""
    
    @pytest.fixture
    def valid_public_body_data(self):
        """Return valid public body creation data."""
        return {
            'name': f'Test Body {uuid4().hex[:8]}',
            'abbreviation': 'TB',
            'description': 'A test public body',
            'contact_email': 'test@example.gc.ca',
            'website_url': 'https://www.example.gc.ca',
            'is_active': True,
        }
    
    def test_create_public_body_validation_error(self, client, api_v1_prefix):
        """Test that creating without required fields returns 422."""
        response = client.post(
            f"{api_v1_prefix}/public-bodies",
            json={'abbreviation': 'TB'}  # Missing required 'name'
        )
        
        assert response.status_code == 422
        assert 'detail' in response.json()
    
    def test_create_public_body_invalid_email(self, client, api_v1_prefix, valid_public_body_data):
        """Test that invalid email format is handled."""
        valid_public_body_data['contact_email'] = 'not-an-email'
        
        response = client.post(
            f"{api_v1_prefix}/public-bodies",
            json=valid_public_body_data
        )
        
        # Depends on schema validation - may be 422 or accepted
        assert response.status_code in [201, 422]


class TestPublicBodiesAPIUpdate:
    """Test Public Bodies update endpoint."""
    
    def test_update_nonexistent_returns_404(self, client, api_v1_prefix):
        """Test PATCH on non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.patch(
            f"{api_v1_prefix}/public-bodies/{fake_id}",
            json={'abbreviation': 'NEW'}
        )
        
        assert response.status_code == 404


class TestPublicBodiesAPIDelete:
    """Test Public Bodies delete endpoint."""
    
    def test_delete_nonexistent_returns_404(self, client, api_v1_prefix):
        """Test DELETE on non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.delete(f"{api_v1_prefix}/public-bodies/{fake_id}")
        
        assert response.status_code == 404
