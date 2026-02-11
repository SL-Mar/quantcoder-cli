"""Core modules for QuantCoder."""

# Lazy imports to avoid loading heavy dependencies at import time
__all__ = ["ArticleProcessor", "LLMHandler", "SummaryStore", "lint_qc_code", "LintResult"]


def __getattr__(name):
    if name == "ArticleProcessor":
        from .processor import ArticleProcessor
        return ArticleProcessor
    if name == "LLMHandler":
        from .llm import LLMHandler
        return LLMHandler
    if name == "SummaryStore":
        from .summary_store import SummaryStore
        return SummaryStore
    if name == "lint_qc_code":
        from .qc_linter import lint_qc_code
        return lint_qc_code
    if name == "LintResult":
        from .qc_linter import LintResult
        return LintResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
