"""Learning systems for error patterns and performance analysis."""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

from quantcoder.autonomous.database import (
    CompilationError,
    LearningDatabase,
    PerformancePattern,
)


@dataclass
class ErrorPattern:
    """Represents an identified error pattern."""

    pattern_type: str
    description: str
    code_snippet: str
    suggested_fix: str | None = None
    confidence: float = 0.5


@dataclass
class SuccessPattern:
    """Represents a successful strategy pattern."""

    pattern_type: str
    description: str
    examples: list[str]
    avg_sharpe: float


class ErrorLearner:
    """Learns from compilation and validation errors."""

    def __init__(self, db: LearningDatabase):
        self.db = db

        # Common error patterns to recognize
        self.error_patterns = {
            "import_error": r"ModuleNotFoundError|ImportError|No module named",
            "name_error": r"NameError|name '(\w+)' is not defined",
            "attribute_error": r"AttributeError|has no attribute '(\w+)'",
            "type_error": r"TypeError|unexpected argument|got \d+ arguments",
            "syntax_error": r"SyntaxError|invalid syntax",
            "indentation_error": r"IndentationError|unexpected indent",
            "api_error": r"QCAlgorithm|QuantConnect API",
        }

    def analyze_error(self, error_message: str, code: str) -> ErrorPattern:
        """Analyze an error and identify its pattern."""
        # Classify error type
        error_type = self._classify_error(error_message)

        # Extract relevant code snippet
        code_snippet = self._extract_relevant_code(error_message, code)

        # Check if we've seen this before
        similar_errors = self.db.get_similar_errors(error_type, limit=5)

        # Get suggested fix if available
        error_hash = self._hash_error(error_message)
        known_fix = self.db.get_fix_for_error(error_hash)

        suggested_fix = None
        confidence = 0.5

        if known_fix:
            suggested_fix = known_fix["solution_pattern"]
            confidence = known_fix["confidence"]
        elif similar_errors:
            # Use most common fix from similar errors
            suggested_fix = self._get_most_common_fix(similar_errors)
            confidence = 0.6

        return ErrorPattern(
            pattern_type=error_type,
            description=error_message,
            code_snippet=code_snippet,
            suggested_fix=suggested_fix,
            confidence=confidence,
        )

    def learn_from_fix(
        self, error_message: str, original_code: str, fixed_code: str, success: bool
    ):
        """Learn from a successful or failed fix attempt."""
        error_type = self._classify_error(error_message)
        code_snippet = self._extract_relevant_code(error_message, original_code)

        # Calculate the fix that was applied
        fix_applied = self._extract_fix(original_code, fixed_code)

        # Store in database
        error = CompilationError(
            error_type=error_type,
            error_message=error_message,
            code_snippet=code_snippet,
            fix_applied=fix_applied,
            success=success,
        )
        self.db.add_compilation_error(error)

        # If successful, add to successful fixes
        if success:
            error_hash = self._hash_error(error_message)
            self.db.add_successful_fix(error_hash, fix_applied)

    def get_common_errors(self, limit: int = 10) -> list[dict]:
        """Get most common error types and their fix rates."""
        return self.db.get_common_error_types(limit)

    def get_success_rate(self) -> float:
        """Get overall error fix success rate."""
        common_errors = self.get_common_errors()
        if not common_errors:
            return 0.0

        total = sum(e["count"] for e in common_errors)
        fixed = sum(e["fixed_count"] for e in common_errors)

        return fixed / total if total > 0 else 0.0

    def _classify_error(self, error_message: str) -> str:
        """Classify error type based on message."""
        for error_type, pattern in self.error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return error_type
        return "unknown_error"

    def _extract_relevant_code(self, error_message: str, code: str) -> str:
        """Extract the code snippet relevant to the error."""
        # Try to extract line number from error
        line_match = re.search(r"line (\d+)", error_message)
        if line_match:
            line_num = int(line_match.group(1))
            lines = code.split("\n")
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 2)
            return "\n".join(lines[start:end])

        # Return first 10 lines as fallback
        return "\n".join(code.split("\n")[:10])

    def _hash_error(self, error_message: str) -> str:
        """Create a hash for error pattern matching."""
        # Normalize error message (remove line numbers, variable names)
        normalized = re.sub(r"\d+", "N", error_message)
        normalized = re.sub(r"'[^']*'", "VAR", normalized)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _get_most_common_fix(self, similar_errors: list[dict]) -> str:
        """Get most common fix from similar errors."""
        fixes = [e["fix_applied"] for e in similar_errors if e["fix_applied"]]
        if not fixes:
            return None
        counter = Counter(fixes)
        return counter.most_common(1)[0][0]

    def _extract_fix(self, original: str, fixed: str) -> str:
        """Extract what changed between original and fixed code."""
        # Simple diff - in production you'd use difflib
        if original == fixed:
            return "no_change"

        # Extract added lines
        original_lines = set(original.split("\n"))
        fixed_lines = set(fixed.split("\n"))
        added = fixed_lines - original_lines

        if added:
            return "added: " + "; ".join(list(added)[:3])

        return "modified_code"


class PerformanceLearner:
    """Learns from backtest performance patterns."""

    def __init__(self, db: LearningDatabase):
        self.db = db

        # Performance thresholds
        self.good_sharpe = 1.0
        self.acceptable_sharpe = 0.5
        self.max_acceptable_drawdown = -0.30

    def analyze_poor_performance(
        self, strategy_code: str, strategy_type: str, sharpe: float, drawdown: float
    ) -> dict[str, str]:
        """Analyze why a strategy performed poorly."""
        issues = []

        # Check Sharpe ratio
        if sharpe < self.acceptable_sharpe:
            issues.append(f"Low Sharpe ratio ({sharpe:.2f})")

            # Check if this strategy type typically performs better
            stats = self.db.get_performance_stats(strategy_type)
            if stats and stats.get("avg_sharpe", 0) > sharpe + 0.3:
                issues.append(
                    f"Below average for {strategy_type} " f"(avg: {stats['avg_sharpe']:.2f})"
                )

        # Check drawdown
        if drawdown < self.max_acceptable_drawdown:
            issues.append(f"Excessive drawdown ({drawdown:.1%})")

        # Analyze code patterns
        code_issues = self._analyze_code_issues(strategy_code)
        issues.extend(code_issues)

        # Store the pattern
        pattern = PerformancePattern(
            strategy_type=strategy_type,
            sharpe_ratio=sharpe,
            max_drawdown=drawdown,
            common_issues="; ".join(issues),
            success_patterns="",
        )
        self.db.add_performance_pattern(pattern)

        return {
            "issues": issues,
            "recommendations": self._generate_recommendations(issues, strategy_type),
        }

    def identify_success_patterns(
        self, strategy_code: str, strategy_type: str, sharpe: float, drawdown: float
    ) -> SuccessPattern:
        """Identify what made a strategy successful."""
        success_indicators = []

        # Extract successful patterns from code
        if "SetWarmUp" in strategy_code:
            success_indicators.append("Uses warm-up period")

        if "RiskManagement" in strategy_code:
            success_indicators.append("Implements risk management")

        if "Insight" in strategy_code:
            success_indicators.append("Uses Insight-based signals")

        if re.search(r"def.*Update.*:", strategy_code):
            success_indicators.append("Has Update method")

        # Store success pattern
        pattern = PerformancePattern(
            strategy_type=strategy_type,
            sharpe_ratio=sharpe,
            max_drawdown=drawdown,
            common_issues="",
            success_patterns="; ".join(success_indicators),
        )
        self.db.add_performance_pattern(pattern)

        return SuccessPattern(
            pattern_type=strategy_type,
            description=f"Successful {strategy_type} strategy",
            examples=success_indicators,
            avg_sharpe=sharpe,
        )

    def get_best_practices(self, strategy_type: str) -> list[str]:
        """Get best practices for a strategy type based on learnings."""
        stats = self.db.get_performance_stats(strategy_type)

        practices = []
        if stats and stats.get("avg_sharpe", 0) >= self.good_sharpe:
            practices.append(f"Average Sharpe ratio: {stats['avg_sharpe']:.2f}")

        # Get common success patterns
        # In production, you'd query successful strategies and extract patterns
        practices.extend(
            [
                "Use proper warm-up periods",
                "Implement risk management",
                "Use Insight-based signals",
                "Include position sizing logic",
                "Add proper universe filtering",
            ]
        )

        return practices

    def _analyze_code_issues(self, code: str) -> list[str]:
        """Analyze code for common performance issues."""
        issues = []

        # Check for missing components
        if "SetWarmUp" not in code:
            issues.append("Missing warm-up period")

        if "RiskManagement" not in code and "ManageRisk" not in code:
            issues.append("No risk management")

        if "Universe" not in code and "AddEquity" not in code:
            issues.append("Poor universe selection")

        # Check for potential overfitting
        magic_numbers = len(re.findall(r"\b\d+\.\d+\b", code))
        if magic_numbers > 10:
            issues.append("Too many magic numbers (potential overfitting)")

        return issues

    def _generate_recommendations(self, issues: list[str], strategy_type: str) -> list[str]:
        """Generate recommendations based on identified issues."""
        recommendations = []

        for issue in issues:
            if "warm-up" in issue.lower():
                recommendations.append("Add SetWarmUp() to allow indicators to initialize")
            elif "risk" in issue.lower():
                recommendations.append("Implement RiskManagementModel or position sizing")
            elif "universe" in issue.lower():
                recommendations.append("Improve universe selection with better filters")
            elif "drawdown" in issue.lower():
                recommendations.append("Add stop-loss or trailing stop mechanisms")
            elif "sharpe" in issue.lower():
                recommendations.append("Review signal quality and entry/exit timing")
            elif "overfitting" in issue.lower():
                recommendations.append("Use parameters from optimization, not hardcoded values")

        # Add strategy-specific recommendations
        best_practices = self.get_best_practices(strategy_type)
        recommendations.extend(best_practices[:2])  # Top 2 practices

        return recommendations
