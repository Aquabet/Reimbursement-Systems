import boto3
import json
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from ocr_worker.mcp_extractor import MockMcpExtractor
from ocr_worker.policy_engine import RuleEngine, ValidationContext, ValidationResult
from ocr_worker.rules import (
    MealCapRule,
    ReceiptCountRule,
    CategoryExceptionRule,
)


def get_receipt_context(receipt_id, db_session):
    """Get the full context for validation including report-level aggregates."""
    # Get receipt and report info
    result = db_session.execute(
        text(
            """SELECT r.report_id
            FROM receipt r
            WHERE r.id = :receipt_id"""
        ),
        {"receipt_id": receipt_id},
    ).fetchone()

    if not result:
        raise ValueError(f"Receipt {receipt_id} not found")

    report_id = result[0]

    # Get OCR results
    ocr_result = db_session.execute(
        text(
            """SELECT extracted_text, status
            FROM ocr_result
            WHERE receipt_id = :receipt_id"""
        ),
        {"receipt_id": receipt_id},
    ).fetchone()

    if not ocr_result:
        raise ValueError(f"OCR result not found for receipt {receipt_id}")

    extracted_text = ocr_result[0]

    # Get report aggregates
    agg_result = db_session.execute(
        text(
            """SELECT COUNT(*) as receipt_count
            FROM receipt
            WHERE report_id = :report_id"""
        ),
        {"report_id": report_id},
    ).fetchone()

    report_receipt_count = agg_result[0]

    return report_id, extracted_text, report_receipt_count


def update_validation_result(
    receipt_id,
    extracted_amount,
    extracted_date,
    extracted_vendor,
    extracted_category,
    status,
    compliance_notes,
    normalized_amount,
    policy_version,
    applied_rules,
    db_session,
):
    """Update or insert validation result in database."""
    try:
        # Try to update existing record
        result = db_session.execute(
            text(
                """UPDATE validation_result
                SET extracted_amount = :amount,
                    extracted_date = :date,
                    extracted_vendor = :vendor,
                    extracted_category = :category,
                    status = :status,
                    compliance_notes = :notes,
                    normalized_amount = :normalized,
                    policy_version = :policy_version,
                    applied_rules = :applied_rules
                WHERE receipt_id = :receipt_id"""
            ),
            {
                "receipt_id": receipt_id,
                "amount": extracted_amount,
                "date": extracted_date,
                "vendor": extracted_vendor,
                "category": extracted_category,
                "status": status,
                "notes": compliance_notes,
                "normalized": normalized_amount,
                "policy_version": policy_version,
                "applied_rules": json.dumps(applied_rules),
            },
        )

        if result.rowcount == 0:
            # Insert new record
            db_session.execute(
                text(
                    """INSERT INTO validation_result
                    (receipt_id, extracted_amount, extracted_date,
                     extracted_vendor, extracted_category, status,
                     compliance_notes, normalized_amount, policy_version, applied_rules)
                    VALUES (:receipt_id, :amount, :date, :vendor, :category,
                            :status, :notes, :normalized, :policy_version, :applied_rules)"""
                ),
                {
                    "receipt_id": receipt_id,
                    "amount": extracted_amount,
                    "date": extracted_date,
                    "vendor": extracted_vendor,
                    "category": extracted_category,
                    "status": status,
                    "notes": compliance_notes,
                    "normalized": normalized_amount,
                    "policy_version": policy_version,
                    "applied_rules": json.dumps(applied_rules),
                },
            )

        db_session.commit()
        print(f"Successfully updated validation result for receipt_id: {receipt_id}")
    except Exception as e:
        print(f"Error updating validation result: {e}")
        db_session.rollback()
        raise


def process_validation_job(message_body):
    """Process a validation job using the policy engine."""
    receipt_id = message_body["receipt_id"]

    print(f"\n=== Processing validation for receipt_id: {receipt_id} ===")

    # Create validation context
    policy_config = {
        "meal_daily_cap": 75.00,
        "meal_single_cap": 50.00,
        "max_receipts_per_report": 20,
        "category_limits": {
            "meal": {"cap": 75.00, "requires_justification": True},
            "travel": {"cap": 200.00, "requires_justification": False},
            "fuel": {"cap": 100.00, "requires_justification": False},
            "office": {"cap": 50.00, "requires_justification": False},
            "other": {"cap": 25.00, "requires_justification": False},
        },
    }

    engine = create_engine(os.environ.get("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get receipt context
        report_id, extracted_text, report_receipt_count = get_receipt_context(
            receipt_id, session
        )

        # Extract fields (in production, these would come from real MCP)
        extractor = MockMcpExtractor()
        fields = extractor.extract_fields(extracted_text)

        # Create validation context
        context = ValidationContext(
            receipt_id=receipt_id,
            report_id=report_id,
            extracted_amount=fields.get("amount"),
            extracted_date=fields.get("date"),
            extracted_vendor=fields.get("vendor"),
            extracted_category=fields.get("category"),
            report_total_amount=0.0,  # Would need to calculate from other receipts
            report_receipt_count=report_receipt_count,
        )

        # Apply rules
        policy_engine = RuleEngine(policy_version="1.0")
        policy_engine.load_policy(policy_config)

        results = policy_engine.validate_receipt(context)

        # Determine overall status
        overall_status = policy_engine.get_overall_status(results)

        # Calculate normalized amount
        normalized_amount = policy_engine.calculate_normalized_amount(results)

        # Build compliance notes
        compliance_notes = []
        applied_rules = []

        for result in results:
            applied_rules.append(result.rule_name)
            if result.status != "PASS":
                compliance_notes.append(f"{result.rule_name}: {result.message}")

        # Save validation result
        update_validation_result(
            receipt_id=receipt_id,
            extracted_amount=fields.get("amount"),
            extracted_date=fields.get("date"),
            extracted_vendor=fields.get("vendor"),
            extracted_category=fields.get("category"),
            status=overall_status,
            compliance_notes="; ".join(compliance_notes) if compliance_notes else "All validation rules passed",
            normalized_amount=normalized_amount,
            policy_version="1.0",
            applied_rules=applied_rules,
            db_session=session,
        )

        print(f"  Status: {overall_status}")
        print(f"  Normalized Amount: ${normalized_amount:.2f}" if normalized_amount else "  Normalized Amount: None")
        print(f"  Rules Applied: {', '.join(applied_rules)}")

        return overall_status, normalized_amount, results

    finally:
        session.close()


def main():
    load_dotenv()

    sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION"))
    queue_url = os.environ.get("SQS_VALIDATION_QUEUE_URL")

    print("Validation Worker started. Waiting for messages...")
    print(f"Queue URL: {queue_url}")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=20
        )

        if "Messages" in response:
            message = response["Messages"][0]
            receipt_handle = message["ReceiptHandle"]
            message_id = message["MessageId"]
            body = json.loads(message["Body"])

            receipt_id = body.get("receipt_id")
            if not receipt_id:
                print(f"Invalid message (no receipt_id): {message_id}")
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                continue

            try:
                # Process validation
                process_validation_job(body)

                # Delete message on success
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                print(f"✓ Message deleted from validation queue for receipt_id: {receipt_id}")

            except Exception as e:
                print(f"✗ Error processing validation job for receipt_id {receipt_id}: {e}")
                # Message will be retried via SQS visibility timeout and DLQ

        else:
            print("No messages in queue.")
            import time
            time.sleep(1)


if __name__ == "__main__":
    main()
