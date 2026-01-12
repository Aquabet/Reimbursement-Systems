from typing import Optional, Dict, List
from datetime import datetime
from .policy_engine import ValidationRule, ValidationContext, ValidationResult


class MealCapRule(ValidationRule):
    """Rule: Enforce meal spending caps per day and per receipt."""

    def __init__(self, daily_cap: float = 75.00, single_receipt_cap: float = 50.00):
        self.daily_cap = daily_cap
        self.single_receipt_cap = single_receipt_cap
        self._receipts_by_date: Dict[str, List[float]] = {}

    @property
    def rule_name(self) -> str:
        return "meal_cap"

    def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate meal expenses against caps."""
        # Only apply to meal expenses
        if context.extracted_category != "meal":
            return ValidationResult(
                rule_name=self.rule_name,
                status="PASS",
                message="Not a meal expense, rule not applicable",
            )

        amount = context.extracted_amount
        if amount is None:
            return ValidationResult(
                rule_name=self.rule_name,
                status="FAIL",
                message="Could not extract amount from receipt",
            )

        violations = []
        normalized_amount = amount

        # Check single receipt cap
        if amount > self.single_receipt_cap:
            violations.append(
                f"Single meal receipt of ${amount:.2f} exceeds cap of ${self.single_receipt_cap:.2f}"
            )
            normalized_amount = self.single_receipt_cap

        # Check daily cap if we have date information
        if context.extracted_date:
            date_key = context.extracted_date
            if date_key not in self._receipts_by_date:
                self._receipts_by_date[date_key] = []

            # Add this receipt's amount (normalized if already over single receipt cap)
            self._receipts_by_date[date_key].append(normalized_amount)

            # Calculate daily total
            daily_total = sum(self._receipts_by_date[date_key])

            if daily_total > self.daily_cap:
                # Adjust normalized amount to fit within daily cap
                previous_total = daily_total - normalized_amount
                remaining_cap = max(0, self.daily_cap - previous_total)
                normalized_amount = min(normalized_amount, remaining_cap)

                violations.append(
                    f"Daily meal total of ${daily_total:.2f} exceeds cap of ${self.daily_cap:.2f}"
                )
        else:
            violations.append("Could not validate daily cap: no date extracted")

        if violations:
            status = "FAIL" if amount > self.single_receipt_cap or normalized_amount < amount else "WARN"
            return ValidationResult(
                rule_name=self.rule_name,
                status=status,
                message="; ".join(violations),
                normalized_amount=normalized_amount,
                metadata={
                    "daily_cap": self.daily_cap,
                    "single_receipt_cap": self.single_receipt_cap,
                },
            )
        else:
            return ValidationResult(
                rule_name=self.rule_name,
                status="PASS",
                message=f"Meal expense of ${amount:.2f} is within policy limits",
                normalized_amount=amount,
            )


class ReceiptCountRule(ValidationRule):
    """Rule: Limit the number of receipts per reimbursement report."""

    def __init__(self, max_receipts_per_report: int = 20):
        self.max_receipts = max_receipts_per_report

    @property
    def rule_name(self) -> str:
        return "receipt_count_limit"

    def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate that report doesn't exceed receipt count limit."""
        receipt_count = context.report_receipt_count

        if receipt_count > self.max_receipts:
            return ValidationResult(
                rule_name=self.rule_name,
                status="FAIL",
                message=f"Report has {receipt_count} receipts, exceeding limit of {self.max_receipts}",
                metadata={
                    "max_receipts": self.max_receipts,
                    "actual_receipts": receipt_count,
                },
            )
        elif receipt_count >= self.max_receipts * 0.9:  # 90% of limit
            return ValidationResult(
                rule_name=self.rule_name,
                status="WARN",
                message=f"Report has {receipt_count} receipts, approaching limit of {self.max_receipts}",
                metadata={
                    "max_receipts": self.max_receipts,
                    "actual_receipts": receipt_count,
                },
            )
        else:
            return ValidationResult(
                rule_name=self.rule_name,
                status="PASS",
                message=f"Report has {receipt_count} receipts, within limit of {self.max_receipts}",
                metadata={
                    "max_receipts": self.max_receipts,
                    "actual_receipts": receipt_count,
                },
            )


class CategoryExceptionRule(ValidationRule):
    """Rule: Apply category-specific limits and exceptions."""

    def __init__(self, category_limits: Optional[Dict[str, Dict]] = None):
        # Default category limits
        self.category_limits = category_limits or {
            "meal": {"cap": 75.00, "requires_justification": True},
            "travel": {"cap": 200.00, "requires_justification": False},
            "fuel": {"cap": 100.00, "requires_justification": False},
            "office": {"cap": 50.00, "requires_justification": False},
            "other": {"cap": 25.00, "requires_justification": False},
        }

    @property
    def rule_name(self) -> str:
        return "category_limits"

    def validate(self, context: ValidationContext) -> ValidationResult:
        """Validate receipt against category-specific limits."""
        category = context.extracted_category
        amount = context.extracted_amount

        if not category or category not in self.category_limits:
            return ValidationResult(
                rule_name=self.rule_name,
                status="WARN",
                message=f"Unknown or unclassified category: {category}",
                metadata={"known_categories": list(self.category_limits.keys())},
            )

        if amount is None:
            return ValidationResult(
                rule_name=self.rule_name,
                status="FAIL",
                message="Could not extract amount from receipt",
            )

        category_config = self.category_limits[category]
        cap = category_config["cap"]
        requires_justification = category_config["requires_justification"]

        if amount > cap:
            if requires_justification:
                return ValidationResult(
                    rule_name=self.rule_name,
                    status="WARN",
                    message=f"{category.upper()} expense of ${amount:.2f} exceeds cap of ${cap:.2f} - justification required",
                    normalized_amount=cap,
                    metadata={
                        "category": category,
                        "cap": cap,
                        "amount": amount,
                        "requires_justification": True,
                    },
                )
            else:
                return ValidationResult(
                    rule_name=self.rule_name,
                    status="FAIL",
                    message=f"{category.upper()} expense of ${amount:.2f} exceeds limit of ${cap:.2f}",
                    normalized_amount=cap,
                    metadata={
                        "category": category,
                        "cap": cap,
                        "amount": amount,
                        "requires_justification": False,
                    },
                )
        else:
            return ValidationResult(
                rule_name=self.rule_name,
                status="PASS",
                message=f"{category.upper()} expense of ${amount:.2f} is within limit of ${cap:.2f}",
                normalized_amount=amount,
                metadata={
                    "category": category,
                    "cap": cap,
                    "amount": amount,
                },
            )
