"""Core modules for QuantCoder."""

# Lazy imports to avoid loading heavy dependencies at import time
__all__ = ["ArticleProcessor", "LLMHandler", "SummaryStore"]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
