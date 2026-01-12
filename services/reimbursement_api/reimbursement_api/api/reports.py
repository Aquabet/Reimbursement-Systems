from flask import Blueprint, jsonify, request, g

from reimbursement_api.application.services import ReportService
from reimbursement_api.application.report_aggregation_service import (
    ReportAggregationService,
    StateTransitionError,
)
from reimbursement_api.application.review_service import ReviewService
from reimbursement_api.application.audit_service import AuditService
from reimbursement_api.infrastructure.auth import (
    jwt_required,
    require_permission,
    require_roles,
    RBAC,
    get_current_user_id,
    get_current_user_email,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/v1/reports")
report_service = ReportService()
aggregation_service = ReportAggregationService()
review_service = ReviewService()
audit_service = AuditService()


@reports_bp.route("", methods=["POST"])
@jwt_required()
@require_permission("create_report")
def create_report():
    data = request.get_json()
    # Add user_id to report data
    data["user_id"] = get_current_user_id()
    report = report_service.create_report(data)
    return jsonify(report.to_dict()), 201


@reports_bp.route("/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    detailed = request.args.get("detailed", "false").lower() == "true"
    report = report_service.get_report(report_id)

    # Check ownership or reviewer/admin access
    current_user_id = get_current_user_id()
    user_role = g.user.get("role") if g.user else None

    if report.user_id != current_user_id and user_role not in [RBAC.REVIEWER, RBAC.ADMIN]:
        return jsonify({"error": "You do not have permission to view this report"}), 403

    if detailed:
        return jsonify(report.to_detailed_dict())
    else:
        return jsonify(report.to_dict())


@reports_bp.route("/<int:report_id>/summary", methods=["GET"])
@jwt_required()
def get_report_summary(report_id):
    """Get comprehensive report summary with receipt validation results."""
    try:
        report = report_service.get_report(report_id)

        # Check ownership or reviewer/admin access
        current_user_id = get_current_user_id()
        user_role = g.user.get("role") if g.user else None

        if report.user_id != current_user_id and user_role not in [RBAC.REVIEWER, RBAC.ADMIN]:
            return jsonify({"error": "You do not have permission to view this report"}), 403

        summary = aggregation_service.get_report_summary(report_id)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/<int:report_id>/submit", methods=["POST"])
@jwt_required()
@require_permission("submit_report")
def submit_report(report_id):
    """Submit a report for approval."""
    try:
        # Verify report ownership
        report = report_service.get_report(report_id)
        if report.user_id != get_current_user_id():
            return jsonify({"error": "You can only submit your own reports"}), 403

        summary, warnings = aggregation_service.submit_report(
            report_id=report_id,
            user_id=get_current_user_id(),
            user_email=get_current_user_email(),
        )
        response = {"report": summary["report"], "warnings": warnings}

        if warnings:
            response["message"] = "Report submitted successfully with warnings"

        return jsonify(response), 200
    except StateTransitionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to submit report: {str(e)}"}), 500


@reports_bp.route("/<int:report_id>/approve", methods=["POST"])
@jwt_required()
@require_roles([RBAC.REVIEWER, RBAC.ADMIN])
def approve_report(report_id):
    """Approve a submitted report."""
    data = request.get_json() or {}
    reviewer_notes = data.get("reviewer_notes")

    try:
        report = aggregation_service.approve_report(
            report_id=report_id,
            user_id=get_current_user_id(),
            user_email=get_current_user_email(),
            reviewer_notes=reviewer_notes,
        )
        return jsonify({"report": report, "message": "Report approved successfully"}), 200
    except StateTransitionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to approve report: {str(e)}"}), 500


@reports_bp.route("/<int:report_id>/reject", methods=["POST"])
@jwt_required()
@require_roles([RBAC.REVIEWER, RBAC.ADMIN])
def reject_report(report_id):
    """Reject a report."""
    data = request.get_json()

    if not data or "rejection_reason" not in data:
        return jsonify({"error": "rejection_reason is required"}), 400

    rejection_reason = data["rejection_reason"]

    try:
        report = aggregation_service.reject_report(
            report_id=report_id,
            rejection_reason=rejection_reason,
            user_id=get_current_user_id(),
            user_email=get_current_user_email(),
        )
        return jsonify({"report": report, "message": "Report rejected"}), 200
    except StateTransitionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to reject report: {str(e)}"}), 500


@reports_bp.route("/review/inbox", methods=["GET"])
@jwt_required()
@require_roles([RBAC.REVIEWER, RBAC.ADMIN])
def get_review_inbox():
    """Get the review inbox with reports pending review."""
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    try:
        inbox_data = review_service.get_review_inbox(
            status=status, page=page, per_page=per_page
        )
        return jsonify(inbox_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/review/<int:report_id>", methods=["GET"])
@jwt_required()
@require_roles([RBAC.REVIEWER, RBAC.ADMIN])
def get_report_for_review(report_id):
    """Get detailed report information for review."""
    try:
        report_details = review_service.get_report_details_for_review(report_id)
        return jsonify(report_details), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@reports_bp.route("/<int:report_id>/audit-trail", methods=["GET"])
@jwt_required()
def get_audit_trail(report_id):
    """Get the complete audit trail for a report."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    # Verify report access
    try:
        report = report_service.get_report(report_id)
        current_user_id = get_current_user_id()
        user_role = g.user.get("role") if g.user else None

        if report.user_id != current_user_id and user_role not in [RBAC.REVIEWER, RBAC.ADMIN]:
            return jsonify({"error": "You do not have permission to view this audit trail"}), 403

        audit_data = audit_service.get_audit_trail_paginated(
            report_id=report_id, page=page, per_page=per_page
        )
        return jsonify(audit_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@reports_bp.route("/<int:report_id>/status-history", methods=["GET"])
@jwt_required()
def get_status_history(report_id):
    """Get the status history for a report."""
    try:
        history = aggregation_service.get_status_history(report_id)
        return jsonify(history), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404
