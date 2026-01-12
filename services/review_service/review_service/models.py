from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    user_id = db.Column(db.String(100), nullable=False, index=True)
    total_receipts = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'user_id': self.user_id,
            'total_receipts': self.total_receipts,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
        }

    def to_detailed_dict(self):
        data = self.to_dict()
        # Detailed view would include receipts, audit trail, etc.
        # This would be fetched from Receipt Service via API
        return data


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20))
    user_id = db.Column(db.String(100), nullable=False, index=True)
    user_email = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    metadata = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        metadata = {}
        if self.metadata:
            try:
                metadata = json.loads(self.metadata)
            except:
                pass

        return {
            'id': self.id,
            'report_id': self.report_id,
            'action': self.action,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'notes': self.notes,
            'metadata': metadata,
            'created_at': self.created_at.isoformat(),
        }


class ReviewComment(db.Model):
    __tablename__ = 'review_comments'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, nullable=False, index=True)
    reviewer_id = db.Column(db.String(100), nullable=False, index=True)
    reviewer_email = db.Column(db.String(255), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    is_rejection_comment = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'reviewer_id': self.reviewer_id,
            'reviewer_email': self.reviewer_email,
            'comment': self.comment,
            'is_rejection_comment': self.is_rejection_comment,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
