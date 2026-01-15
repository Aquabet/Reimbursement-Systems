from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json
from typing import TYPE_CHECKING

db = SQLAlchemy()

if TYPE_CHECKING:
    from flask_sqlalchemy.model import Model as _Model

    class Model(_Model):
        __abstract__ = True
else:
    Model = db.Model


class Receipt(Model):
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    s3_object_key = db.Column(db.String(500))
    content_type = db.Column(db.String(100))
    status = db.Column(db.String(20), nullable=False, default="UPLOADED")
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    expense_date = db.Column(db.Date, nullable=True)
    vendor = db.Column(db.String(200))
    category = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    ocr_completed_at = db.Column(db.DateTime, nullable=True)
    validation_completed_at = db.Column(db.DateTime, nullable=True)

    # Validation results (as JSON)
    validation_results = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "s3_object_key": self.s3_object_key,
            "content_type": self.content_type,
            "status": self.status,
            "amount": float(self.amount) if self.amount else None,
            "expense_date": self.expense_date.isoformat()
            if self.expense_date
            else None,
            "vendor": self.vendor,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ocr_completed_at": self.ocr_completed_at.isoformat()
            if self.ocr_completed_at
            else None,
            "validation_completed_at": self.validation_completed_at.isoformat()
            if self.validation_completed_at
            else None,
        }

    def to_detailed_dict(self):
        data = self.to_dict()

        # Add validation results if available
        if self.validation_results:
            try:
                data["validation_results"] = json.loads(self.validation_results)
            except json.JSONDecodeError:
                data["validation_results"] = None

        return data


class ValidationResult(Model):
    __tablename__ = "validation_results"

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, nullable=False, index=True)
    report_id = db.Column(db.Integer, nullable=False, index=True)
    extracted_text = db.Column(db.Text)
    extracted_amount = db.Column(db.Numeric(10, 2))
    extracted_date = db.Column(db.Date)
    extracted_vendor = db.Column(db.String(200))
    extracted_category = db.Column(db.String(100))
    validation_status = db.Column(db.String(20), nullable=False, default="PENDING")
    validation_rules = db.Column(db.Text)  # JSON of rule results
    normalized_amount = db.Column(db.Numeric(10, 2))
    warnings = db.Column(db.Text)  # JSON array of warnings
    errors = db.Column(db.Text)  # JSON array of errors
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def to_dict(self):
        validation_rules = []
        warnings = []
        errors = []

        if self.validation_rules:
            try:
                validation_rules = json.loads(self.validation_rules)
            except json.JSONDecodeError:
                pass

        if self.warnings:
            try:
                warnings = json.loads(self.warnings)
            except json.JSONDecodeError:
                pass

        if self.errors:
            try:
                errors = json.loads(self.errors)
            except json.JSONDecodeError:
                pass

        return {
            "id": self.id,
            "receipt_id": self.receipt_id,
            "report_id": self.report_id,
            "extracted_text": self.extracted_text,
            "extracted_amount": float(self.extracted_amount)
            if self.extracted_amount
            else None,
            "extracted_date": self.extracted_date.isoformat()
            if self.extracted_date
            else None,
            "extracted_vendor": self.extracted_vendor,
            "extracted_category": self.extracted_category,
            "validation_status": self.validation_status,
            "validation_rules": validation_rules,
            "normalized_amount": float(self.normalized_amount)
            if self.normalized_amount
            else None,
            "warnings": warnings,
            "errors": errors,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
