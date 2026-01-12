import hashlib
import os

from reimbursement_api.domain.models import Receipt, Report
from reimbursement_api.infrastructure.database import db
from reimbursement_api.infrastructure.local_storage import LocalStorage
from reimbursement_api.infrastructure.s3_storage import S3Storage


class ReportService:
    def create_report(self, data):
        new_report = Report(title=data.get("title"), description=data.get("description"))
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
