import json
import os
from io import BytesIO

import pytest

from reimbursement_api.app import create_app
from reimbursement_api.domain.models import Report
from reimbursement_api.infrastructure.database import db


@pytest.fixture
def app(mocker):
    mocker.patch("boto3.client")
    # Set the UPLOAD_FOLDER for testing
    upload_folder = "test_uploads"
    os.environ["UPLOAD_FOLDER"] = upload_folder
    os.environ["STORAGE_TYPE"] = "local"

    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        # Create a report to associate receipts with
        test_report = Report(title="Test Report for Receipts")
        db.session.add(test_report)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

    # Clean up the test upload folder
    if os.path.exists(upload_folder):  # noqa: PTH110
        for file in os.listdir(upload_folder):
            os.remove(os.path.join(upload_folder, file))  # noqa: PTH107, PTH118
        os.rmdir(upload_folder)  # noqa: PTH106


@pytest.fixture
def client(app):
    return app.test_client()


def test_upload_receipt(client):
    """Test uploading a new receipt."""
    data = {"receipt": (BytesIO(b"my file contents"), "test.jpg"), "report_id": 1}
    response = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 201  # noqa: PLR2004
    response_data = json.loads(response.data)
    assert response_data["filename"] == "test.jpg"
    assert "storage_path" in response_data


def test_upload_duplicate_receipt(client):
    """Test uploading a receipt that has already been uploaded."""
    file_content = b"duplicate file content"
    data = {"receipt": (BytesIO(file_content), "duplicate.jpg"), "report_id": 1}
    # Upload the first time
    response1 = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")
    assert response1.status_code == 201  # noqa: PLR2004

    # Upload the second time
    # Need to create a new BytesIO object because the file pointer is at the end
    data["receipt"] = (BytesIO(file_content), "duplicate.jpg")
    response2 = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")
    assert response2.status_code == 200  # noqa: PLR2004
    response_data = json.loads(response2.data)
    assert "This receipt has already been uploaded." in response_data["message"]


def test_upload_receipt_no_file(client):
    """Test uploading with no file part."""
    data = {"report_id": 1}
    response = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400  # noqa: PLR2004
    response_data = json.loads(response.data)
    assert "No receipt file provided" in response_data["error"]


def test_upload_receipt_no_report_id(client):
    """Test uploading without a report_id."""
    data = {"receipt": (BytesIO(b"my file contents"), "test.jpg")}
    response = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400  # noqa: PLR2004
    response_data = json.loads(response.data)
    assert "report_id is required" in response_data["error"]


def test_upload_receipt_publishes_sqs_message(client, mocker):
    """Test that uploading a new receipt publishes an SQS message."""
    mock_send_message = mocker.patch("reimbursement_api.infrastructure.message_queue.SqsMessageQueue.send_message")

    data = {"receipt": (BytesIO(b"my file contents"), "test.jpg"), "report_id": 1}
    response = client.post("/v1/receipts/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 201  # noqa: PLR2004
    mock_send_message.assert_called_once()
