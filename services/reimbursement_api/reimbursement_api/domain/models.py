from reimbursement_api.infrastructure.database import db
from datetime import datetime


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(120), nullable=False)

    description = db.Column(db.Text, nullable=True)

    # Ownership
    user_id = db.Column(db.String(100), nullable=False, index=True)  # Who owns this report

    # Status machine fields
    status = db.Column(
        db.String(20), nullable=False, default="DRAFT"
    )  # DRAFT, SUBMITTED, REVIEW_PENDING, APPROVED, REJECTED

    submitted_at = db.Column(db.DateTime, nullable=True)

    approved_at = db.Column(db.DateTime, nullable=True)

    rejected_at = db.Column(db.DateTime, nullable=True)

    rejection_reason = db.Column(db.Text, nullable=True)

    # Report totals and summary
    total_receipts = db.Column(db.Integer, nullable=False, default=0)

    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)

    valid_receipts = db.Column(db.Integer, nullable=False, default=0)

    invalid_receipts = db.Column(db.Integer, nullable=False, default=0)

    warning_receipts = db.Column(db.Integer, nullable=False, default=0)

    receipts = db.relationship("Receipt", backref="report", lazy=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "total_receipts": self.total_receipts,
            "total_amount": float(self.total_amount) if self.total_amount else 0.0,
            "valid_receipts": self.valid_receipts,
            "invalid_receipts": self.invalid_receipts,
            "warning_receipts": self.warning_receipts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_detailed_dict(self):
        """Return detailed report with receipt information."""
        basic_data = self.to_dict()
        basic_data["receipts"] = [receipt.to_dict() for receipt in self.receipts]
        return basic_data


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    report_id = db.Column(db.Integer, db.ForeignKey("report.id"), nullable=False)
    report = db.relationship("Report", backref=db.backref("audit_logs", lazy=True))

    # Who performed the action
    user_id = db.Column(db.String(100), nullable=True)  # User who performed the action

    user_email = db.Column(db.String(255), nullable=True)  # Email of the user

    # What action was performed
    action = db.Column(db.String(50), nullable=False)  # SUBMIT, APPROVE, REJECT, RETURN_TO_DRAFT, etc.

    # Old and new states (for immutability)
    from_status = db.Column(db.String(20), nullable=True)

    to_status = db.Column(db.String(20), nullable=True)

    # Additional context
    notes = db.Column(db.Text, nullable=True)  # Optional notes/reasons

    metadata_json = db.Column(db.Text, nullable=True)  # JSON blob for additional context

    # Timestamp (immutable)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "notes": self.notes,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat(),
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


class ValidationResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.id"), nullable=False, unique=True)
    receipt = db.relationship(
        "Receipt", backref=db.backref("validation_result", uselist=False)
    )

    # OCR extracted data
    extracted_amount = db.Column(db.Numeric(10, 2), nullable=True)
    extracted_date = db.Column(db.Date, nullable=True)
    extracted_vendor = db.Column(db.String(255), nullable=True)
    extracted_category = db.Column(db.String(100), nullable=True)

    # Validation fields
    status = db.Column(
        db.String(20), nullable=False, default="PENDING"
    )  # PASS, WARN, FAIL
    compliance_notes = db.Column(db.Text, nullable=True)
    normalized_amount = db.Column(db.Numeric(10, 2), nullable=True)

    # Polic/Rule references
    policy_version = db.Column(db.String(50), nullable=True)
    applied_rules = db.Column(db.Text, nullable=True)  # JSON list of rule names

    def to_dict(self):
        return {
            "id": self.id,
            "receipt_id": self.receipt_id,
            "extracted_amount": float(self.extracted_amount) if self.extracted_amount else None,
            "extracted_date": self.extracted_date.isoformat() if self.extracted_date else None,
            "extracted_vendor": self.extracted_vendor,
            "extracted_category": self.extracted_category,
            "status": self.status,
            "compliance_notes": self.compliance_notes,
            "normalized_amount": float(self.normalized_amount) if self.normalized_amount else None,
            "policy_version": self.policy_version,
            "applied_rules": self.applied_rules,
        }
