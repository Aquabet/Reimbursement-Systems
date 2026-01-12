from flask import Blueprint, jsonify, request

from reimbursement_api.application.services import ReportService

reports_bp = Blueprint("reports", __name__, url_prefix="/v1/reports")
report_service = ReportService()


@reports_bp.route("", methods=["POST"])
def create_report():
    data = request.get_json()
    report = report_service.create_report(data)
    return jsonify(report.to_dict()), 201


@reports_bp.route("/<int:report_id>", methods=["GET"])
def get_report(report_id):
    report = report_service.get_report(report_id)
    return jsonify(report.to_dict())
