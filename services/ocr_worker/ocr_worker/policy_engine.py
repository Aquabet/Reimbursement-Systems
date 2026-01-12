from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import json


@dataclass
class ValidationContext:
    """Context passed to validation rules containing receipt and OCR data."""

    receipt_id: int
    report_id: int

    extracted_amount: Optional[float]
    extracted_date: Optional[str]
    extracted_vendor: Optional[str]
    extracted_category: Optional[str]

    # Report-level aggregates
    report_total_amount: float = 0.0
    report_receipt_count: int = 0
    report_receipts_by_category: Dict[str, int] = None

    def __post_init__(self):
        if self.report_receipts_by_category is None:
            self.report_receipts_by_category = {}


@dataclass
class ValidationResult:
    """Result of applying a validation rule."""

    rule_name: str
    status: str  # PASS, WARN, FAIL
    message: str
    normalized_amount: Optional[float] = None
    metadata: Optional[Dict] = None

    def to_dict(self):
        return {
            "rule_name": self.rule_name,
            "status": self.status,
            "message": self.message,
            "normalized_amount": self.normalized_amount,
            "metadata": self.metadata,
        }


class ValidationRule(ABC):
    """Abstract base class for validation rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Return the name of this rule."""
        pass

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Apply the rule and return a validation result."""
        pass


class RuleEngine:
    """Engine that applies multiple validation rules to a receipt."""

    def __init__(self, policy_version: str = "1.0"):
        self.policy_version = policy_version
        self.rules: List[ValidationRule] = []

    def load_policy(self, policy_config: Dict):
        """Load policy configuration and initialize rules."""
        # In production, this would load from a database or file
        # For now, we hardcode the policy
        self.rules = [
            MealCapRule(
                daily_cap=policy_config.get("meal_daily_cap", 75.00),
                single_receipt_cap=policy_config.get("meal_single_cap", 50.00),
            ),
            ReceiptCountRule(
                max_receipts_per_report=policy_config.get("max_receipts_per_report", 20),
            ),
            CategoryExceptionRule(
                category_limits=policy_config.get("category_limits", {
                    "meal": {"cap": 75.00, "requires_justification": True},
                    "travel": {"cap": 200.00, "requires_justification": False},
                    "other": {"cap": 50.00, "requires_justification": False},
                }),
            ),
        ]

    def validate_receipt(self, context: ValidationContext) -> List[ValidationResult]:
        """Apply all rules to the receipt and return results."""
        results = []

        for rule in self.rules:
            try:
                result = rule.validate(context)
                results.append(result)
            except Exception as e:
                # Log error but continue with other rules
                results.append(
                    ValidationResult(
                        rule_name=rule.rule_name,
                        status="FAIL",
                        message=f"Rule execution error: {str(e)}",
                    )
                )

        return results

    def get_overall_status(self, results: List[ValidationResult]) -> str:
        """Determine overall validation status from rule results."""
        statuses = [result.status for result in results]

        if any(status == "FAIL" for status in statuses):
            return "FAIL"
        elif any(status == "WARN" for status in statuses):
            return "WARN"
        else:
            return "PASS"

    def calculate_normalized_amount(self, results: List[ValidationResult]) -> Optional[float]:
        """Calculate the normalized reimbursement amount based on rules."""
        # Find the minimum normalized amount from all rules
        normalized_amounts = [
            result.normalized_amount
            for result in results
            if result.normalized_amount is not None
        ]

        if not normalized_amounts:
            return None

        # Use the minimum normalized amount (most restrictive rule)
        return min(normalized_amounts)
