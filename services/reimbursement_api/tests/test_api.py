import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from reimbursement_api.app import create_app
from reimbursement_api.infrastructure.database import db


def generate_jwt_token(user_id="test_user", role=None):
    if role is None:
        role = "submitter"
    payload = {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, "mock-jwt-secret-key", algorithm="HS256")


@pytest.fixture
def app(mocker):
    mocker.patch("reimbursement_api.app.get_secret", return_value="mock-jwt-secret-key")
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_report(client):
    """Test creating a new report."""
    token = generate_jwt_token()
    response = client.post(
        "/v1/reports",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-ID": "test_user",
            "X-User-Email": "test@example.com",
        },
        data=json.dumps({"title": "Test Report", "description": "A test report description."}),
        content_type="application/json",
    )
    assert response.status_code == 201  # noqa: PLR2004
    data = json.loads(response.data)
    assert data["title"] == "Test Report"
    assert "id" in data


def test_get_report(client):
    """Test getting a single report."""
    # First, create a report to get
    token = generate_jwt_token()
    post_response = client.post(
        "/v1/reports",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-ID": "test_user",
            "X-User-Email": "test@example.com",
        },
        data=json.dumps({"title": "Another Test Report", "description": "Another description."}),
        content_type="application/json",
    )
    assert post_response.status_code == 201  # noqa: PLR2004
    post_data = json.loads(post_response.data)
    report_id = post_data["id"]

    # Now, get the report
    get_response = client.get(
        f"/v1/reports/{report_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-ID": "test_user",
            "X-User-Email": "test@example.com",
        },
    )
    assert get_response.status_code == 200  # noqa: PLR2004
    get_data = json.loads(get_response.data)
    assert get_data["id"] == report_id
    assert get_data["title"] == "Another Test Report"


def test_get_nonexistent_report(client):
    """Test getting a report that does not exist."""
    token = generate_jwt_token()
    response = client.get(
        "/v1/reports/999",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-ID": "test_user",
            "X-User-Email": "test@example.com",
        },
    )
    assert response.status_code == 404  # noqa: PLR2004
