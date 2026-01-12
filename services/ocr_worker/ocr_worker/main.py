import boto3
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from ocr_worker.storage_reader import StorageReaderFactory
from ocr_worker.mcp_client import McpClient


def determine_mime_type(filename):
    """Determine MIME type based on file extension"""
    if not filename:
        return "image/jpeg"

    ext = filename.lower().split('.')[-1]
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'pdf': 'application/pdf',
        'tiff': 'image/tiff',
        'tif': 'image/tiff'
    }
    return mime_types.get(ext, "image/jpeg")


def process_ocr_job(message_body):
    """Process a single OCR job"""
    receipt_id = message_body["receipt_id"]
    storage_path = message_body["storage_path"]
    filename = message_body.get("filename", "")

    print(f"Processing receipt_id: {receipt_id}")
    print(f"Storage path: {storage_path}")

    # Read the file from storage
    aws_region = os.environ.get("AWS_REGION")
    storage_reader = StorageReaderFactory.create_reader(storage_path, aws_region)
    image_bytes = storage_reader.read_file(storage_path)
    print(f"Successfully read file: {len(image_bytes)} bytes")

    # Extract text using MCP
    mcp_client = McpClient(os.environ.get("MCP_BASE_URL", "http://localhost:8080"))
    try:
        mime_type = determine_mime_type(filename)
        extracted_text = mcp_client.extract_text(image_bytes, mime_type)
        print(f"Successfully extracted text: {len(extracted_text)} characters")
        return extracted_text
    finally:
        mcp_client.close()


def update_ocr_status(receipt_id, status, extracted_text, db_session):
    """Update OCR result status in database"""
    try:
        db_session.execute(
            text(
                """UPDATE ocr_result
                SET status = :status, extracted_text = :text
                WHERE receipt_id = :id"""
            ),
            {"status": status, "text": extracted_text, "id": receipt_id},
        )
        db_session.commit()
        print(f"Successfully updated OCR result for receipt_id: {receipt_id}")
    except Exception as e:
        print(f"Error updating database: {e}")
        db_session.rollback()
        raise


def main():
    load_dotenv()

    sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION"))
    queue_url = os.environ.get("SQS_QUEUE_URL")

    engine = create_engine(os.environ.get("DATABASE_URL"))
    Session = sessionmaker(bind=engine)

    print("Worker started. Waiting for messages...")
    print(f"Queue URL: {queue_url}")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=20
        )

        if "Messages" in response:
            message = response["Messages"][0]
            receipt_handle = message["ReceiptHandle"]
            message_id = message["MessageId"]
            body = json.loads(message["Body"])

            receipt_id = body.get("receipt_id")
            if not receipt_id:
                print(f"Invalid message (no receipt_id): {message_id}")
                # Delete invalid messages
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                continue

            session = Session()

            try:
                # Process the OCR job
                print(f"\n=== Processing receipt_id: {receipt_id} ===")
                extracted_text = process_ocr_job(body)

                # Update database with success
                update_ocr_status(receipt_id, "SUCCESS", extracted_text, session)

                # Delete message from queue on success
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                print(f"✓ Message deleted from queue for receipt_id: {receipt_id}")

            except Exception as e:
                error_msg = str(e)
                print(f"\n✗ Error processing OCR job for receipt_id {receipt_id}: {error_msg}")

                # Update database with failure
                try:
                    update_ocr_status(receipt_id, "FAILED", error_msg, session)
                finally:
                    session.close()

                # For permanent failures (vs transient), we might want to delete the message
                # to prevent infinite retries. SQS DLQ will handle messages that exceed max receives.
                # For now, we let SQS handle retries via visibility timeout and DLQ.

            finally:
                if session:
                    session.close()
        else:
            print("No messages in queue.")
            # Add a small sleep to prevent hammering the queue when empty
            import time
            time.sleep(1)


if __name__ == "__main__":
    main()
