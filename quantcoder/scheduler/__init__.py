"""Automated scheduler module for QuantCoder.

This module provides:
- Scheduled strategy discovery and backtesting
- Notion integration for publishing strategy articles
- Automated end-to-end workflow orchestration
"""

from .notion_client import NotionClient, StrategyArticle
from .article_generator import ArticleGenerator, StrategyReport
from .runner import ScheduledRunner, ScheduleConfig, ScheduleInterval
from .automated_pipeline import AutomatedBacktestPipeline, PipelineConfig

__all__ = [
    "NotionClient",
    "StrategyArticle",
    "ArticleGenerator",
    "StrategyReport",
    "ScheduledRunner",
    "ScheduleConfig",
    "ScheduleInterval",
    "AutomatedBacktestPipeline",
    "PipelineConfig",
]
