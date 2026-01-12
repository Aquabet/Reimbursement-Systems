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
