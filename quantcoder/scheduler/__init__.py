"""Automated scheduler module for QuantCoder.

This module provides:
- Scheduled strategy discovery and backtesting
- Notion integration for publishing strategy articles
- Automated end-to-end workflow orchestration
"""

from .notion_client import NotionClient
from .article_generator import ArticleGenerator
from .runner import ScheduledRunner
from .automated_pipeline import AutomatedBacktestPipeline

__all__ = [
    "NotionClient",
    "ArticleGenerator",
    "ScheduledRunner",
    "AutomatedBacktestPipeline",
]
