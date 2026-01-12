from reimbursement_api.domain.models import Report
from reimbursement_api.infrastructure.database import db


class ReportService:
    def create_report(self, data):
        new_report = Report(title=data.get("title"), description=data.get("description"))
        db.session.add(new_report)
        db.session.commit()
        return new_report

    def get_report(self, report_id):
        return Report.query.get_or_404(report_id)
