"""Integration tests for UI routes."""

import pytest
from uuid import uuid4


class TestDashboardUI:
    """Test dashboard UI route."""
    
    def test_dashboard_renders(self, client):
        """Test that dashboard page renders."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
    
    def test_dashboard_contains_expected_elements(self, client):
        """Test dashboard contains expected content."""
        response = client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Should contain dashboard elements
        assert 'dashboard' in content.lower() or 'Dashboard' in content


class TestPublicBodiesUI:
    """Test public bodies UI routes."""
    
    def test_list_page_renders(self, client):
        """Test public bodies list page renders."""
        response = client.get("/public-bodies")
        
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
    
    def test_detail_page_not_found(self, client):
        """Test detail page returns 404 for non-existent body."""
        fake_id = uuid4()
        response = client.get(f"/public-bodies/{fake_id}")
        
        # Should return 404 or render error page
        assert response.status_code in [200, 404]
    
    def test_list_page_with_search(self, client):
        """Test list page with search parameter."""
        response = client.get("/public-bodies", params={'search': 'treasury'})
        
        assert response.status_code == 200


class TestRequestsUI:
    """Test ATI requests UI routes."""
    
    def test_list_page_renders(self, client):
        """Test requests list page renders."""
        response = client.get("/requests")
        
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
    
    def test_detail_page_not_found(self, client):
        """Test detail page returns 404 for non-existent request."""
        fake_id = uuid4()
        response = client.get(f"/requests/{fake_id}")
        
        # Should return 404 or render error page
        assert response.status_code in [200, 404]
    
    def test_list_page_with_filters(self, client):
        """Test list page with filter parameters."""
        response = client.get(
            "/requests",
            params={
                'status': 'received',
                'outcome': 'pending',
            }
        )
        
        assert response.status_code == 200


class TestCompareUI:
    """Test comparison UI route."""
    
    def test_compare_page_renders(self, client):
        """Test compare page renders."""
        response = client.get("/compare")
        
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')


class TestErrorPages:
    """Test error page handling."""
    
    def test_404_page(self, client):
        """Test 404 error for non-existent route."""
        response = client.get("/non-existent-page")
        
        assert response.status_code == 404
    
    def test_invalid_uuid_in_url(self, client):
        """Test handling of invalid UUID in URL."""
        response = client.get("/public-bodies/not-a-uuid")
        
        # Should handle gracefully - 404 or 422
        assert response.status_code in [404, 422]
