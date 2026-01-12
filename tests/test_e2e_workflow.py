import pytest
import requests
import time


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration test for the complete reimbursement workflow."""

    def test_complete_reimbursement_workflow(self, api_gateway_url, submitter_token, reviewer_token):
        """Test the complete workflow: create report → add receipts → submit → approve."""

        # Step 1: Create a report
        print("\n1. Creating report...")
        report_data = {
            "title": "January Business Trip",
            "description": "Expenses for San Francisco business trip"
        }

        response = requests.post(
            f"{api_gateway_url}/v1/reports",
            headers={"Authorization": submitter_token},
            json=report_data
        )

        assert response.status_code == 201, f"Failed to create report: {response.text}"
        report = response.json()
        report_id = report["id"]
        print(f"✓ Report created: ID {report_id}")

        # Step 2: Create receipts for the report
        print("\n2. Adding receipts to report...")
        receipts = [
            {
                "report_id": report_id,
                "user_id": "test-submitter",
                "file_name": "hotel_receipt.jpg",
                "s3_object_key": f"receipts/test/hotel_{report_id}.jpg",
                "content_type": "image/jpeg"
            },
            {
                "report_id": report_id,
                "user_id": "test-submitter",
                "file_name": "meal_receipt.jpg",
                "s3_object_key": f"receipts/test/meal_{report_id}.jpg",
                "content_type": "image/jpeg"
            }
        ]

        receipt_ids = []
        for receipt_data in receipts:
            response = requests.post(
                f"{api_gateway_url}/v1/receipts",
                headers={"Authorization": submitter_token},
                json=receipt_data
            )
            assert response.status_code == 201, f"Failed to create receipt: {response.text}"
            receipt = response.json()
            receipt_ids.append(receipt["id"])
            print(f"✓ Receipt created: ID {receipt['id']}")

        # Step 3: Get report summary (should show receipts)
        print("\n3. Getting report summary...")
        response = requests.get(
            f"{api_gateway_url}/v1/reports/{report_id}/summary",
            headers={"Authorization": submitter_token}
        )

        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        summary = response.json()
        print(f"✓ Report summary: {summary['report']['total_receipts']} receipts")

        # Step 4: Submit report
        print("\n4. Submitting report...")
        response = requests.post(
            f"{api_gateway_url}/v1/reports/{report_id}/submit",
            headers={"Authorization": submitter_token}
        )

        assert response.status_code == 200, f"Failed to submit report: {response.text}"
        result = response.json()
        print(f"✓ Report submitted with status: {result['report']['status']}")
        assert result["report"]["status"] == "SUBMITTED"

        # Step 5: Reviewer checks inbox
        print("\n5. Reviewer checking inbox...")
        response = requests.get(
            f"{api_gateway_url}/v1/review/inbox",
            headers={"Authorization": reviewer_token}
        )

        assert response.status_code == 200, f"Failed to get inbox: {response.text}"
        inbox = response.json()
        print(f"✓ Reviewer inbox: {len(inbox['reports'])} pending reports")

        # Find our report in inbox
        report_in_inbox = None
        for r in inbox["reports"]:
            if r["id"] == report_id:
                report_in_inbox = r
                break

        assert report_in_inbox is not None, "Report not found in reviewer inbox"
        print(f"✓ Report found in inbox: {report_in_inbox['title']}")

        # Step 6: Reviewer gets report details
        print("\n6. Reviewer getting report details...")
        response = requests.get(
            f"{api_gateway_url}/v1/review/{report_id}",
            headers={"Authorization": reviewer_token}
        )

        assert response.status_code == 200, f"Failed to get report details: {response.text}"
        report_details = response.json()
        print(f"✓ Report details retrieved: {len(report_details.get('receipts', []))} receipts")

        # Step 7: Reviewer approves report
        print("\n7. Reviewer approving report...")
        approval_data = {
            "reviewer_notes": "All receipts are within policy limits"
        }

        response = requests.post(
            f"{api_gateway_url}/v1/reports/{report_id}/approve",
            headers={"Authorization": reviewer_token},
            json=approval_data
        )

        assert response.status_code == 200, f"Failed to approve report: {response.text}"
        result = response.json()
        print(f"✓ Report approved: {result['report']['status']}")
        assert result["report"]["status"] == "APPROVED"

        # Step 8: Verify report status
        print("\n8. Verifying final report status...")
        response = requests.get(
            f"{api_gateway_url}/v1/reports/{report_id}",
            headers={"Authorization": submitter_token}
        )

        assert response.status_code == 200, f"Failed to get report: {response.text}"
        final_report = response.json()
        print(f"✓ Final report status: {final_report['status']}")
        assert final_report["status"] == "APPROVED"

        # Step 9: Check audit trail
        print("\n9. Checking audit trail...")
        response = requests.get(
            f"{api_gateway_url}/v1/reports/{report_id}/audit-trail",
            headers={"Authorization": submitter_token}
        )

        assert response.status_code == 200, f"Failed to get audit trail: {response.text}"
        audit_trail = response.json()
        print(f"✓ Audit trail: {len(audit_trail.get('audit_logs', []))} entries")
        assert len(audit_trail.get("audit_logs", [])) >= 2  # SUBMITTED and APPROVED

        print("\n" + "="*60)
        print("✅ END-TO-END WORKFLOW TEST PASSED!")
        print("="*60)

    def test_rejection_workflow(self, api_gateway_url, submitter_token, reviewer_token):
        """Test the rejection workflow."""

        # Step 1: Create and submit a report
        report_data = {
            "title": "Invalid Expenses",
            "description": "Test report that will be rejected"
        }

        response = requests.post(
            f"{api_gateway_url}/v1/reports",
            headers={"Authorization": submitter_token},
            json=report_data
        )
        report_id = response.json()["id"]

        # Submit the report
        response = requests.post(
            f"{api_gateway_url}/v1/reports/{report_id}/submit",
            headers={"Authorization": submitter_token}
        )

        # Step 2: Reviewer rejects the report
        rejection_data = {
            "rejection_reason": "Meal expenses exceed $50 limit without justification"
        }

        response = requests.post(
            f"{api_gateway_url}/v1/reports/{report_id}/reject",
            headers={"Authorization": reviewer_token},
            json=rejection_data
        )

        assert response.status_code == 200
        result = response.json()
        assert result["report"]["status"] == "REJECTED"
        assert result["report"]["rejection_reason"] == rejection_data["rejection_reason"]

        print("✅ Rejection workflow test passed!")
