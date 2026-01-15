import pytest
import os
from unittest.mock import MagicMock, patch
from ocr_worker.ocr_worker.storage_reader import StorageReader
from ocr_worker.ocr_worker.mcp_extractor import MCPExtractor


@pytest.fixture
def mock_s3_client():
    with patch("boto3.client") as mock_boto_client:
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_sqs_client():
    with patch("boto3.client") as mock_boto_client:
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs
        yield mock_sqs


@pytest.fixture
def storage_reader(mock_s3_client):
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_ENDPOINT_URL"] = "http://localstack:4566"
    return StorageReader()


@pytest.fixture
def mcp_extractor():
    return MCPExtractor()


class TestStorageReader:
    def test_read_receipt_from_s3_success(self, storage_reader, mock_s3_client):
        mock_s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"mock image content")
        }
        content = storage_reader.read_receipt_from_s3("test/receipt.jpg")
        assert content == b"mock image content"
        mock_s3_client.get_object.assert_called_with(
            Bucket="test-bucket", Key="test/receipt.jpg"
        )

    def test_read_receipt_from_s3_not_found(self, storage_reader, mock_s3_client):
        mock_s3_client.get_object.side_effect = Exception("NoSuchKey")
        content = storage_reader.read_receipt_from_s3("test/nonexistent.jpg")
        assert content is None


class TestMCPExtractor:
    def test_extract_ocr_data_success(self, mcp_extractor):
        mock_response = {
            "text": "Total: $123.45",
            "entities": [
                {"type": "AMOUNT", "text": "$123.45", "value": 123.45},
                {"type": "DATE", "text": "2023-01-01", "value": "2023-01-01"},
                {"type": "VENDOR", "text": "Cafe", "value": "Cafe"},
                {"type": "CATEGORY", "text": "Food", "value": "Food"},
            ],
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            data = mcp_extractor.extract_ocr_data(b"image_bytes")
            assert data["amount"] == 123.45
            assert data["expense_date"] == "2023-01-01"
            assert data["vendor"] == "Cafe"
            assert data["category"] == "Food"

    def test_extract_ocr_data_api_error(self, mcp_extractor):
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Internal Server Error"

            data = mcp_extractor.extract_ocr_data(b"image_bytes")
            assert data is None
