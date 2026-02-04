"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from uuid import uuid4

from src.main import app


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_v1_prefix():
    """Return the API v1 prefix."""
    return "/api/v1"


@pytest.fixture
def sample_public_body_data():
    """Generate sample public body data."""
    return {
        'name': f'Test Body {uuid4().hex[:8]}',
        'abbreviation': 'TB',
        'description': 'A test public body for testing purposes',
        'contact_email': 'test@example.gc.ca',
        'website_url': 'https://www.example.gc.ca',
        'is_active': True,
    }


@pytest.fixture
def sample_ati_request_data():
    """Generate sample ATI request data."""
    submission = date.today() - timedelta(days=15)
    return {
        'request_number': f'ATI-{date.today().year}-{uuid4().hex[:6].upper()}',
        'public_body_id': str(uuid4()),
        'submission_date': submission.isoformat(),
        'due_date': (submission + timedelta(days=30)).isoformat(),
        'request_type': 'non_personal',
        'status': 'received',
        'outcome': 'pending',
        'summary': 'Test ATI request for automated testing',
    }


@pytest.fixture
def sample_csv_ati_requests():
    """Generate sample CSV content for ATI requests."""
    return """request_number,submission_date,due_date,public_body_name,status,outcome,summary
ATI-2024-TEST001,2024-01-15,2024-02-14,Treasury Board,received,pending,Test request 1
ATI-2024-TEST002,2024-01-20,2024-02-19,Health Canada,in_progress,pending,Test request 2
ATI-2024-TEST003,2024-02-01,2024-03-02,Environment Canada,completed,full_disclosure,Test request 3
"""


@pytest.fixture
def sample_csv_public_bodies():
    """Generate sample CSV content for public bodies."""
    return """name,abbreviation,description,contact_email,website_url,is_active
Treasury Board Secretariat,TBS,Central agency,ati@tbs.gc.ca,https://www.tbs.gc.ca,true
Health Canada,HC,Health department,ati@hc.gc.ca,https://www.hc.gc.ca,true
Environment Canada,EC,Environment department,ati@ec.gc.ca,https://www.ec.gc.ca,true
"""


@pytest.fixture
def invalid_csv_content():
    """Generate invalid CSV content for error testing."""
    return """this,is,not,valid
data,without,proper,structure
"""
