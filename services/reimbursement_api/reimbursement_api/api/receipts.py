from flask import Blueprint, jsonify, request

from reimbursement_api.application.services import ReceiptService

receipts_bp = Blueprint("receipts", __name__, url_prefix="/v1/receipts")
receipt_service = ReceiptService()


@receipts_bp.route("/upload", methods=["POST"])
def upload_receipt():
    if "receipt" not in request.files:
        return jsonify({"error": "No receipt file provided"}), 400

    file = request.files["receipt"]
    report_id = request.form.get("report_id")

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not report_id:
        return jsonify({"error": "report_id is required"}), 400

    if file:
        receipt, is_duplicate = receipt_service.create_receipt(file, report_id)
        if is_duplicate:
            return jsonify({"message": "This receipt has already been uploaded.", "receipt": receipt.to_dict()}), 200
        return jsonify(receipt.to_dict()), 201

    return jsonify({"error": "An unexpected error occurred"}), 500
