from reimbursement_api.infrastructure.database import db


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(120), nullable=False)

    description = db.Column(db.Text, nullable=True)

    receipts = db.relationship("Receipt", backref="report", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
        }


class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    report_id = db.Column(db.Integer, db.ForeignKey("report.id"), nullable=False)

    filename = db.Column(db.String(255), nullable=False)

    storage_path = db.Column(db.String(255), nullable=False, unique=True)

    file_hash = db.Column(db.String(64), nullable=False, unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "filename": self.filename,
            "storage_path": self.storage_path,
        }


class OcrResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.id"), nullable=False, unique=True)
    receipt = db.relationship("Receipt", backref=db.backref("ocr_result", uselist=False))
    extracted_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="PENDING")  # e.g., PENDING, SUCCESS, FAILED

    def to_dict(self):
        return {
            "id": self.id,
            "receipt_id": self.receipt_id,
            "extracted_text": self.extracted_text,
            "status": self.status,
        }
