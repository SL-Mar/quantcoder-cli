"""Article generator for strategy reports."""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .notion_client import StrategyArticle

logger = logging.getLogger(__name__)


@dataclass
class StrategyReport:
    """Complete strategy report with all metadata."""
    strategy_name: str
    paper_title: str
    paper_url: str
    paper_authors: List[str]
    paper_abstract: str
    strategy_type: str
    strategy_summary: str
    code_files: Dict[str, str]
    backtest_results: Dict[str, Any]
    quantconnect_project_id: Optional[str] = None
    quantconnect_backtest_id: Optional[str] = None
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()


class ArticleGenerator:
    """Generates formatted articles from strategy reports."""

    def __init__(self, llm_provider=None):
        """Initialize article generator.

        Args:
            llm_provider: Optional LLM provider for enhanced summaries
        """
        self.llm = llm_provider

    def generate_title(self, report: StrategyReport) -> str:
        """Generate an engaging article title.

        Args:
            report: The strategy report

        Returns:
            Generated title string
        """
        strategy_type_display = report.strategy_type.replace("_", " ").title()

        # Extract key metrics
        sharpe = report.backtest_results.get("sharpe_ratio", 0)
        total_return = report.backtest_results.get("total_return", 0)

        # Generate descriptive title
        if sharpe >= 1.5:
            performance = "High-Performance"
        elif sharpe >= 1.0:
            performance = "Strong"
        elif sharpe >= 0.5:
            performance = "Viable"
        else:
            performance = "Experimental"

        return f"{performance} {strategy_type_display} Strategy: {report.strategy_name}"

    def generate_summary(self, report: StrategyReport) -> str:
        """Generate a concise strategy summary.

        Uses LLM if available, otherwise creates a template-based summary.

        Args:
            report: The strategy report

        Returns:
            Summary text
        """
        if self.llm:
            return self._generate_llm_summary(report)
        else:
            return self._generate_template_summary(report)

    def _generate_template_summary(self, report: StrategyReport) -> str:
        """Generate template-based summary."""
        strategy_type = report.strategy_type.replace("_", " ")
        sharpe = report.backtest_results.get("sharpe_ratio", 0)
        total_return = report.backtest_results.get("total_return", 0)
        drawdown = report.backtest_results.get("max_drawdown", 0)

        # Determine strategy characteristics from code
        code_content = "\n".join(report.code_files.values())

        indicators = []
        if "SMA" in code_content or "SimpleMovingAverage" in code_content:
            indicators.append("Simple Moving Average")
        if "EMA" in code_content or "ExponentialMovingAverage" in code_content:
            indicators.append("Exponential Moving Average")
        if "RSI" in code_content or "RelativeStrengthIndex" in code_content:
            indicators.append("RSI")
        if "MACD" in code_content:
            indicators.append("MACD")
        if "BollingerBands" in code_content:
            indicators.append("Bollinger Bands")
        if "ATR" in code_content or "AverageTrueRange" in code_content:
            indicators.append("ATR")

        indicators_text = ", ".join(indicators) if indicators else "custom indicators"

        summary = f"""This {strategy_type} strategy was derived from the research paper "{report.paper_title}".

The algorithm uses {indicators_text} to generate trading signals. """

        if sharpe >= 1.0:
            summary += f"Backtesting shows promising results with a Sharpe ratio of {sharpe:.2f}. "
        else:
            summary += f"Initial backtesting shows a Sharpe ratio of {sharpe:.2f}. "

        if total_return > 0:
            summary += f"The strategy achieved a total return of {total_return:.1%} "
        else:
            summary += f"The strategy had a return of {total_return:.1%} "

        summary += f"with a maximum drawdown of {abs(drawdown):.1%}."

        return summary

    def _generate_llm_summary(self, report: StrategyReport) -> str:
        """Generate LLM-enhanced summary."""
        prompt = f"""Write a concise 2-3 paragraph summary of this trading strategy for a technical audience:

Paper: {report.paper_title}
Strategy Type: {report.strategy_type}
Paper Abstract: {report.paper_abstract[:500]}

Backtest Results:
- Sharpe Ratio: {report.backtest_results.get('sharpe_ratio', 'N/A')}
- Total Return: {report.backtest_results.get('total_return', 'N/A')}
- Max Drawdown: {report.backtest_results.get('max_drawdown', 'N/A')}

Code Preview:
{list(report.code_files.values())[0][:500] if report.code_files else 'Not available'}

Focus on:
1. What the strategy does and how it works
2. Key technical indicators or signals used
3. Performance characteristics and risk profile

Keep it factual and technical. No marketing language."""

        try:
            response = self.llm.generate(prompt, max_tokens=500)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}, falling back to template")
            return self._generate_template_summary(report)

    def generate_notion_article(self, report: StrategyReport) -> StrategyArticle:
        """Generate a StrategyArticle for Notion publishing.

        Args:
            report: The strategy report

        Returns:
            StrategyArticle ready for Notion
        """
        title = self.generate_title(report)
        summary = self.generate_summary(report)

        # Get main code file for snippet
        main_code = report.code_files.get("Main.py", "")
        if not main_code and report.code_files:
            main_code = list(report.code_files.values())[0]

        # Build QuantConnect URL if we have project info
        qc_url = None
        if report.quantconnect_project_id:
            qc_url = f"https://www.quantconnect.com/project/{report.quantconnect_project_id}"

        # Determine tags
        tags = [report.strategy_type.replace("_", " ").title()]

        # Add performance-based tags
        sharpe = report.backtest_results.get("sharpe_ratio", 0)
        if sharpe >= 1.5:
            tags.append("High Sharpe")
        if report.backtest_results.get("total_return", 0) > 0.5:
            tags.append("High Return")
        if abs(report.backtest_results.get("max_drawdown", 0)) < 0.1:
            tags.append("Low Drawdown")

        return StrategyArticle(
            title=title,
            paper_title=report.paper_title,
            paper_url=report.paper_url,
            paper_authors=report.paper_authors,
            strategy_summary=summary,
            strategy_type=report.strategy_type,
            backtest_results=report.backtest_results,
            code_snippet=main_code[:2000] if main_code else None,
            quantconnect_project_url=qc_url,
            tags=tags
        )

    def generate_markdown(self, report: StrategyReport) -> str:
        """Generate a markdown article for local storage.

        Args:
            report: The strategy report

        Returns:
            Markdown formatted article
        """
        title = self.generate_title(report)
        summary = self.generate_summary(report)
        results = report.backtest_results

        md = f"""# {title}

> Based on: [{report.paper_title}]({report.paper_url})
> Authors: {', '.join(report.paper_authors)}
> Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}

## Strategy Summary

{summary}

## Backtest Results

| Metric | Value |
|--------|-------|
| Sharpe Ratio | {results.get('sharpe_ratio', 'N/A'):.2f} |
| Total Return | {results.get('total_return', 0):.2%} |
| Max Drawdown | {results.get('max_drawdown', 0):.2%} |
| Win Rate | {results.get('win_rate', 'N/A')} |
| Period | {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')} |

"""

        # Add QuantConnect link if available
        if report.quantconnect_project_id:
            md += f"""## Algorithm

[View on QuantConnect](https://www.quantconnect.com/project/{report.quantconnect_project_id})

"""

        # Add code files
        md += "## Code\n\n"
        for filename, code in report.code_files.items():
            md += f"### {filename}\n\n```python\n{code}\n```\n\n"

        md += """---

*Generated by QuantCoder - AI-powered algorithmic trading strategy generator*
"""

        return md

    def save_markdown(self, report: StrategyReport, output_dir: Path) -> Path:
        """Save markdown article to file.

        Args:
            report: The strategy report
            output_dir: Directory to save to

        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{report.strategy_name}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = output_dir / filename

        md_content = self.generate_markdown(report)
        filepath.write_text(md_content, encoding="utf-8")

        logger.info(f"Saved markdown article to {filepath}")
        return filepath

    def save_json_report(self, report: StrategyReport, output_dir: Path) -> Path:
        """Save complete report as JSON.

        Args:
            report: The strategy report
            output_dir: Directory to save to

        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{report.strategy_name}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename

        data = {
            "strategy_name": report.strategy_name,
            "paper": {
                "title": report.paper_title,
                "url": report.paper_url,
                "authors": report.paper_authors,
                "abstract": report.paper_abstract
            },
            "strategy": {
                "type": report.strategy_type,
                "summary": self.generate_summary(report)
            },
            "code_files": report.code_files,
            "backtest_results": report.backtest_results,
            "quantconnect": {
                "project_id": report.quantconnect_project_id,
                "backtest_id": report.quantconnect_backtest_id
            },
            "generated_at": report.generated_at.isoformat()
        }

        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")

        logger.info(f"Saved JSON report to {filepath}")
        return filepath
