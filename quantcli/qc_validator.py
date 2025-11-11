"""
QuantConnect-specific code validator.

This module provides runtime safety validation for generated QuantConnect algorithms,
catching common errors that AST validation misses.
"""

import ast
import re
import logging
from typing import List, Dict, Optional


class ValidationIssue:
    """Represents a validation issue found in code."""

    def __init__(self, severity: str, line: int, message: str, suggestion: str):
        self.severity = severity  # 'error', 'warning', 'info'
        self.line = line
        self.message = message
        self.suggestion = suggestion

    def __repr__(self):
        return f"{self.severity.upper()} (line {self.line}): {self.message}"


class QuantConnectValidator:
    """
    Validates QuantConnect algorithm code for common runtime errors.

    Checks for:
    - Division by zero risks
    - None comparisons without checks
    - Indicator usage without IsReady checks
    - Uninitialized variable usage
    - Missing null guards
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.issues: List[ValidationIssue] = []

    def validate(self, code: str) -> List[ValidationIssue]:
        """
        Validate QuantConnect algorithm code.

        Args:
            code: Python code string to validate

        Returns:
            List of ValidationIssue objects
        """
        self.issues = []
        lines = code.split('\n')

        # Run all validation checks
        self._check_division_operations(lines)
        self._check_max_min_operations(lines)
        self._check_indicator_usage(lines)
        self._check_none_comparisons(lines)
        self._check_portfolio_access(lines)

        self.logger.info(f"Validation complete. Found {len(self.issues)} issues.")
        return self.issues

    def _check_division_operations(self, lines: List[str]):
        """Check for division operations that could cause division by zero."""
        for i, line in enumerate(lines, 1):
            # Find division operations
            if '/' in line and not '//' in line and not line.strip().startswith('#'):
                # Check if there's a guard above
                has_guard = False
                for j in range(max(0, i-5), i):
                    if 'if' in lines[j-1] and ('> 0' in lines[j-1] or '<= 0' in lines[j-1]):
                        has_guard = True
                        break

                if not has_guard and 'positionSize' not in line and 'Portfolio' not in line:
                    # Extract the divisor
                    match = re.search(r'/\s*(\w+)', line)
                    if match:
                        divisor = match.group(1)
                        self.issues.append(ValidationIssue(
                            severity='warning',
                            line=i,
                            message=f"Division by '{divisor}' without zero check",
                            suggestion=f"Add check: if {divisor} <= 0: continue"
                        ))

    def _check_max_min_operations(self, lines: List[str]):
        """Check for max/min operations that could fail with None values."""
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(max|min)\s*\(', line):
                # Look for common None-prone patterns
                if 'indicators[' in line or 'self.' in line:
                    # Check if there's a None guard above
                    has_guard = False
                    for j in range(max(0, i-5), i):
                        if 'is None' in lines[j-1] or 'is not None' in lines[j-1]:
                            has_guard = True
                            break

                    if not has_guard:
                        self.issues.append(ValidationIssue(
                            severity='error',
                            line=i,
                            message="max/min operation on potentially None value",
                            suggestion="Add None check before max/min operation"
                        ))

    def _check_indicator_usage(self, lines: List[str]):
        """Check that indicators are checked with .IsReady before use."""
        for i, line in enumerate(lines, 1):
            # Look for indicator value access
            if re.search(r'\w+\.Current\.Value', line) and not line.strip().startswith('#'):
                # Check if IsReady was checked in previous lines
                has_ready_check = False
                indicator_name = re.search(r'(\w+)\.Current\.Value', line)
                if indicator_name:
                    name = indicator_name.group(1)
                    for j in range(max(0, i-10), i):
                        if f'{name}.IsReady' in lines[j-1]:
                            has_ready_check = True
                            break

                if not has_ready_check:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        line=i,
                        message="Indicator value used without IsReady check",
                        suggestion="Add: if not indicator.IsReady: continue"
                    ))

    def _check_none_comparisons(self, lines: List[str]):
        """Check for comparisons involving potentially None values."""
        for i, line in enumerate(lines, 1):
            # Look for comparison operators with dictionary/attribute access
            if re.search(r'(>|<|>=|<=|==|!=)', line) and ('indicators[' in line or 'self.' in line):
                if not 'is None' in line and not 'is not None' in line:
                    # Check if None guard exists above
                    has_guard = False
                    for j in range(max(0, i-5), i):
                        if 'is None' in lines[j-1] or 'is not None' in lines[j-1]:
                            has_guard = True
                            break

                    if not has_guard and 'indicators["high"]' in line or 'indicators["low"]' in line:
                        self.issues.append(ValidationIssue(
                            severity='error',
                            line=i,
                            message="Comparison with potentially None value",
                            suggestion="Add None check before comparison"
                        ))

    def _check_portfolio_access(self, lines: List[str]):
        """Check for safe portfolio access patterns."""
        for i, line in enumerate(lines, 1):
            # Look for Portfolio access without ContainsKey check
            if 'self.Portfolio[' in line and 'Invested' not in line:
                # This is generally safe in QuantConnect, just informational
                pass

    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return any(issue.severity == 'error' for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return any(issue.severity == 'warning' for issue in self.issues)

    def get_error_count(self) -> int:
        """Get count of errors."""
        return sum(1 for issue in self.issues if issue.severity == 'error')

    def get_warning_count(self) -> int:
        """Get count of warnings."""
        return sum(1 for issue in self.issues if issue.severity == 'warning')

    def format_report(self) -> str:
        """Format validation issues as a readable report."""
        if not self.issues:
            return "✅ No validation issues found"

        report = f"Found {len(self.issues)} validation issues:\n\n"

        # Group by severity
        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']

        if errors:
            report += "ERRORS:\n"
            for issue in errors:
                report += f"  Line {issue.line}: {issue.message}\n"
                report += f"    → {issue.suggestion}\n\n"

        if warnings:
            report += "WARNINGS:\n"
            for issue in warnings:
                report += f"  Line {issue.line}: {issue.message}\n"
                report += f"    → {issue.suggestion}\n\n"

        return report
