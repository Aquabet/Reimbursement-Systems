import pytest
from ocr_worker.ocr_worker.policy_engine import PolicyEngine
from ocr_worker.ocr_worker.rules import AmountLimitRule, CategoryRule, DateRangeRule


@pytest.fixture
def policy_engine():
    return PolicyEngine()


class TestPolicyEngine:
    def test_apply_rules_success(self, policy_engine):
        ocr_data = {"amount": 45.00, "expense_date": "2023-01-15", "category": "Travel"}
        rules = [
            AmountLimitRule(limit=50.00, message="Amount exceeds limit"),
            CategoryRule(
                allowed_categories=["Travel", "Food"], message="Category not allowed"
            ),
        ]

        result = policy_engine.apply_rules(ocr_data, rules)
        assert result["status"] == "PASS"
        assert not result["warnings"]
        assert not result["errors"]

    def test_apply_rules_with_warning(self, policy_engine):
        ocr_data = {"amount": 55.00, "expense_date": "2023-01-15", "category": "Travel"}
        rules = [
            AmountLimitRule(
                limit=50.00, message="Amount exceeds limit", severity="WARN"
            )
        ]

        result = policy_engine.apply_rules(ocr_data, rules)
        assert result["status"] == "WARN"
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["message"] == "Amount exceeds limit"

    def test_apply_rules_with_error(self, policy_engine):
        ocr_data = {
            "amount": 100.00,
            "expense_date": "2023-01-15",
            "category": "Office",
        }
        rules = [
            AmountLimitRule(
                limit=50.00, message="Amount exceeds limit", severity="FAIL"
            ),
            CategoryRule(
                allowed_categories=["Travel", "Food"],
                message="Category not allowed",
                severity="FAIL",
            ),
        ]

        result = policy_engine.apply_rules(ocr_data, rules)
        assert result["status"] == "FAIL"
        assert len(result["errors"]) == 2
        assert result["errors"][0]["message"] == "Amount exceeds limit"
        assert result["errors"][1]["message"] == "Category not allowed"


class TestRules:
    def test_amount_limit_rule(self):
        rule = AmountLimitRule(
            limit=50.00, message="Amount exceeds limit", severity="WARN"
        )
        assert rule.evaluate({"amount": 45.00}) is None
        assert rule.evaluate({"amount": 55.00}) == {
            "message": "Amount exceeds limit",
            "severity": "WARN",
        }

    def test_category_rule(self):
        rule = CategoryRule(
            allowed_categories=["Travel", "Food"],
            message="Category not allowed",
            severity="FAIL",
        )
        assert rule.evaluate({"category": "Travel"}) is None
        assert rule.evaluate({"category": "Office"}) == {
            "message": "Category not allowed",
            "severity": "FAIL",
        }

    def test_date_range_rule(self):
        rule = DateRangeRule(
            start_date="2023-01-01",
            end_date="2023-01-31",
            message="Date out of range",
            severity="WARN",
        )
        assert rule.evaluate({"expense_date": "2023-01-15"}) is None
        assert rule.evaluate({"expense_date": "2023-02-01"}) == {
            "message": "Date out of range",
            "severity": "WARN",
        }
