import pytest
import requests
import time


def wait_for_service(url, timeout=60):
    """Wait for service to be available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)
    return False


@pytest.fixture(scope="session")
def api_gateway_url():
    """API Gateway URL."""
    return "http://localhost:8080"


@pytest.fixture(scope="session")
def services_ready(api_gateway_url):
    """Wait for all services to be ready."""
    print("\nWaiting for services to be ready...")

    # Wait for API Gateway
    assert wait_for_service(api_gateway_url), "API Gateway not ready"
    print("✓ API Gateway ready")

    # Wait for backend services
    services = [
        ("http://localhost:5000", "Report Service"),
        ("http://localhost:5001", "Receipt Service"),
        ("http://localhost:5002", "Review Service"),
    ]

    for url, name in services:
        assert wait_for_service(url), f"{name} not ready"
        print(f"✓ {name} ready")

    return True


@pytest.fixture
def submitter_token():
    """JWT token for submitter role."""
    # This is a test JWT token with submitter role
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZTEzNTdlZjItZDZmZi00NWE5LWJmODQtMDc2ZDU4YTJmNTczIiwicm9sZSI6InN1Ym1pdHRlciIsInVzZXJfZW1haWwiOiJzdWJtaXR0ZXJAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTl9.mock_signature"


@pytest.fixture
def reviewer_token():
    """JWT token for reviewer role."""
    # This is a test JWT token with reviewer role
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZjI0NjhkZjMtZTdmZi00NWI5LWJmODQtMDc2ZDU4YTJmNTczIiwicm9sZSI6InJldmlld2VyIiwidXNlcl9lbWFpbCI6InJldmlld2VyQGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.mock_signature"
