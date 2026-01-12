import json
import re
from datetime import datetime
from typing import Dict, Optional


class MockMcpExtractor:
    """Mock MCP extractor that parses OCR text and extracts key fields.

    In production, this would call the real MCP OCR service.
    """

    def extract_fields(self, ocr_text: str) -> Dict:
        """Extract amount, date, vendor, and category from OCR text."""
        result = {
            "amount": self._extract_amount(ocr_text),
            "date": self._extract_date(ocr_text),
            "vendor": self._extract_vendor(ocr_text),
            "category": self._extract_category(ocr_text),
        }
        return result

    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract the largest monetary amount from the text."""
        # Look for patterns like $12.34, 12.34, etc.
        patterns = [
            r'\$?\d+\.\d{2}',  # $12.34 or 12.34
            r'\$?\d+\.\d{1}',  # $12.3 or 12.3
            r'\$?\d+',  # $12 or 12
        ]

        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up the match
                cleaned = match.replace('$', '')
                try:
                    amount = float(cleaned)
                    # Filter out unreasonable values (< 0.01 or > 10000)
                    if 0.01 <= amount <= 10000:
                        amounts.append(amount)
                except ValueError:
                    continue

        # Return the maximum amount found (most receipts list items then total)
        return max(amounts) if amounts else None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract a date from the text."""
        # Common date patterns
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or MM/DD/YY
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY or MM-DD-YY
            r'\d{4}/\d{1,2}/\d{1,2}',  # YYYY/MM/DD
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    date_str = matches[0]
                    # Try to parse the date
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts[2]) == 2:
                            # Two-digit year
                            year = int(parts[2]) + 2000
                            return f"{year:04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                        elif len(parts[2]) == 4:
                            return f"{parts[2]:04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                    elif '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts[0]) == 4:
                            # Already YYYY-MM-DD
                            return date_str
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_vendor(self, text: str) -> Optional[str]:
        """Extract vendor/merchant name from text."""
        # Look for common restaurant/store patterns
        lines = text.split('\n')
        for line in lines[:3]:  # Usually in first few lines
            line = line.strip()
            if len(line) > 3 and not any(char.isdigit() for char in line):
                # Skip lines with numbers (addresses, phone numbers)
                if 'LLC' in line or 'Inc' in line or line.isupper():
                    return line.strip()

        # Return first non-empty line if no better match
        for line in lines:
            if line.strip():
                return line.strip()[:100]

        return "Unknown Vendor"

    def _extract_category(self, text: str) -> Optional[str]:
        """Extract category from text."""
        text_lower = text.lower()

        # Keywords for categories
        category_keywords = {
            "meal": ["restaurant", "cafe", "food", "meal", "dining", "coffee", "lunch", "dinner"],
            "travel": ["airline", "hotel", "uber", "lyft", "taxi", "flight", "travel", "transport"],
            "office": ["office", "supplies", "staples", "amazon", "best buy"],
            "fuel": ["gas", "fuel", "shell", "exxon", "chevron"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category

        return "other"
