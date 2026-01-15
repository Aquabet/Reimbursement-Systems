import hashlib
import os

from reimbursement_api.domain.models import OcrResult, Receipt, Report
from reimbursement_api.infrastructure.database import db
from reimbursement_api.infrastructure.local_storage import LocalStorage
from reimbursement_api.infrastructure.message_queue import SqsMessageQueue
from reimbursement_api.infrastructure.s3_storage import S3Storage


class ReportService:
    def create_report(self, data):
        new_report = Report(title=data.get("title"), description=data.get("description"), user_id=data.get("user_id"))
        db.session.add(new_report)
        db.session.commit()
        return new_report

    def get_report(self, report_id):
        return Report.query.get_or_404(report_id)


class ReceiptService:
    def __init__(self):
        if os.environ.get("STORAGE_TYPE") == "s3":
            self.storage = S3Storage(os.environ.get("S3_BUCKET_NAME"))
        else:
            self.storage = LocalStorage(os.environ.get("UPLOAD_FOLDER", "uploads"))
        self.message_queue = SqsMessageQueue()

    def create_receipt(self, file, report_id):
        file_hash = self._hash_file(file)

        # Check for duplicates
        existing_receipt = Receipt.query.filter_by(file_hash=file_hash).first()
        if existing_receipt:
            return existing_receipt, True  # Return the existing receipt and a flag indicating it's a duplicate

        # Save file and metadata
        storage_path = self.storage.save(file, file.filename)
        new_receipt = Receipt(
            report_id=report_id, filename=file.filename, storage_path=storage_path, file_hash=file_hash
        )
        db.session.add(new_receipt)
        db.session.commit()

        # Create a pending OCR result and publish a job
        ocr_result = OcrResult(receipt_id=new_receipt.id, status="PENDING")
        db.session.add(ocr_result)
        db.session.commit()

        self.message_queue.send_message(
            os.environ.get("SQS_QUEUE_URL"),
            {"receipt_id": new_receipt.id, "storage_path": storage_path, "filename": file.filename},
        )

        return new_receipt, False

    def _hash_file(self, file):
        hasher = hashlib.sha256()
        # Reset file pointer to the beginning
        file.seek(0)
        buf = file.read()
        hasher.update(buf)
        # Reset file pointer again so the file can be saved
        file.seek(0)
        return hasher.hexdigest()
