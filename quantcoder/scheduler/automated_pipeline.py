"""Automated end-to-end pipeline for strategy generation and publishing."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from quantcoder.config import Config
from quantcoder.autonomous.pipeline import AutonomousPipeline
from quantcoder.autonomous.database import LearningDatabase
from .notion_client import NotionClient, StrategyArticle
from .article_generator import ArticleGenerator, StrategyReport

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class PipelineConfig:
    """Configuration for the automated pipeline."""
    # Search configuration
    search_queries: List[str] = field(default_factory=lambda: [
        "momentum trading strategy",
        "mean reversion trading",
        "statistical arbitrage",
        "factor investing",
        "machine learning trading"
    ])
    papers_per_query: int = 5

    # Strategy selection - batch limit for strategies per run
    min_sharpe_ratio: float = 0.5  # Acceptance criteria for keeping algo
    max_strategies_per_run: int = 10  # Batch limit (configurable)

    # Backtest configuration
    backtest_start_date: str = "2020-01-01"
    backtest_end_date: str = "2024-01-01"

    # Output configuration
    output_dir: Path = field(default_factory=lambda: Path.home() / ".quantcoder" / "automated_strategies")
    save_markdown: bool = True
    save_json: bool = True

    # Notion publishing - articles for successful strategies only
    publish_to_notion: bool = True
    notion_min_sharpe: float = 0.5  # Same as acceptance criteria by default

    # Paper tracking (avoid reprocessing)
    processed_papers_file: Path = field(default_factory=lambda: Path.home() / ".quantcoder" / "processed_papers.json")


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    papers_found: int = 0
    papers_processed: int = 0
    strategies_generated: int = 0
    strategies_passed_backtest: int = 0
    strategies_published: int = 0
    best_strategy: Optional[Dict] = None
    errors: List[str] = field(default_factory=list)

    @property
    def duration(self) -> Optional[timedelta]:
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "papers_found": self.papers_found,
            "papers_processed": self.papers_processed,
            "strategies_generated": self.strategies_generated,
            "strategies_passed_backtest": self.strategies_passed_backtest,
            "strategies_published": self.strategies_published,
            "best_strategy": self.best_strategy,
            "errors": self.errors
        }


class AutomatedBacktestPipeline:
    """Fully automated pipeline: Papers -> Strategies -> Backtest -> Notion."""

    def __init__(
        self,
        config: Optional[Config] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        notion_client: Optional[NotionClient] = None
    ):
        """Initialize the automated pipeline.

        Args:
            config: QuantCoder configuration
            pipeline_config: Pipeline-specific configuration
            notion_client: Pre-configured Notion client (optional)
        """
        self.config = config or Config.load()
        self.pipeline_config = pipeline_config or PipelineConfig()

        # Initialize components
        self.autonomous = AutonomousPipeline(config=self.config, demo_mode=False)
        self.article_generator = ArticleGenerator()

        # Initialize Notion client
        if notion_client:
            self.notion = notion_client
        else:
            self.notion = NotionClient()

        # Track processed papers
        self.processed_papers = self._load_processed_papers()

    def _load_processed_papers(self) -> set:
        """Load set of already processed paper URLs/DOIs."""
        papers_file = self.pipeline_config.processed_papers_file
        if papers_file.exists():
            try:
                with open(papers_file, 'r') as f:
                    data = json.load(f)
                return set(data.get("processed", []))
            except Exception as e:
                logger.warning(f"Could not load processed papers: {e}")
        return set()

    def _save_processed_papers(self):
        """Save processed papers to file."""
        papers_file = self.pipeline_config.processed_papers_file
        try:
            papers_file.parent.mkdir(parents=True, exist_ok=True)
            with open(papers_file, 'w') as f:
                json.dump({"processed": list(self.processed_papers)}, f)
        except Exception as e:
            logger.warning(f"Could not save processed papers: {e}")

    def _mark_paper_processed(self, paper: Dict):
        """Mark a paper as processed."""
        identifier = paper.get('doi') or paper.get('url') or paper.get('title')
        if identifier:
            self.processed_papers.add(identifier)
            self._save_processed_papers()

    def _is_paper_processed(self, paper: Dict) -> bool:
        """Check if a paper has already been processed."""
        identifier = paper.get('doi') or paper.get('url') or paper.get('title')
        return identifier in self.processed_papers if identifier else False

    async def run(self) -> PipelineResult:
        """Execute the full automated pipeline.

        Returns:
            PipelineResult with run statistics
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = PipelineResult(
            run_id=run_id,
            started_at=datetime.now()
        )

        console.print(Panel.fit(
            f"[bold cyan]Automated Strategy Pipeline[/bold cyan]\n\n"
            f"Run ID: {run_id}\n"
            f"Queries: {len(self.pipeline_config.search_queries)}\n"
            f"Min Sharpe: {self.pipeline_config.min_sharpe_ratio}\n"
            f"Publish to Notion: {self.pipeline_config.publish_to_notion}",
            title="Starting Pipeline"
        ))

        try:
            # Step 1: Discover papers
            console.print("\n[cyan]Step 1: Discovering research papers...[/cyan]")
            all_papers = await self._discover_papers()
            result.papers_found = len(all_papers)
            console.print(f"[green]Found {len(all_papers)} papers[/green]")

            # Filter out already processed papers
            new_papers = [p for p in all_papers if not self._is_paper_processed(p)]
            console.print(f"[dim]New papers to process: {len(new_papers)}[/dim]")

            if not new_papers:
                console.print("[yellow]No new papers to process[/yellow]")
                result.completed_at = datetime.now()
                return result

            # Step 2: Generate and backtest strategies
            console.print("\n[cyan]Step 2: Generating and backtesting strategies...[/cyan]")
            successful_strategies = []

            for i, paper in enumerate(new_papers[:self.pipeline_config.max_strategies_per_run * 2]):
                console.print(f"\n[dim]Processing paper {i+1}/{min(len(new_papers), self.pipeline_config.max_strategies_per_run * 2)}[/dim]")
                console.print(f"[bold]{paper.get('title', 'Unknown')[:80]}...[/bold]")

                try:
                    strategy_result = await self._process_paper(paper)
                    result.papers_processed += 1

                    if strategy_result:
                        result.strategies_generated += 1

                        # Check if it passes our threshold
                        sharpe = strategy_result.get('backtest_results', {}).get('sharpe_ratio', 0)
                        if sharpe >= self.pipeline_config.min_sharpe_ratio:
                            result.strategies_passed_backtest += 1
                            successful_strategies.append(strategy_result)
                            console.print(f"[green]Strategy passed with Sharpe {sharpe:.2f}[/green]")

                            # Track best strategy
                            if not result.best_strategy or sharpe > result.best_strategy.get('sharpe_ratio', 0):
                                result.best_strategy = {
                                    'name': strategy_result['name'],
                                    'sharpe_ratio': sharpe,
                                    'paper_title': paper.get('title')
                                }
                        else:
                            console.print(f"[yellow]Strategy below threshold (Sharpe {sharpe:.2f})[/yellow]")

                    self._mark_paper_processed(paper)

                    # Stop if we have enough successful strategies
                    if len(successful_strategies) >= self.pipeline_config.max_strategies_per_run:
                        console.print(f"\n[green]Reached target of {self.pipeline_config.max_strategies_per_run} strategies[/green]")
                        break

                except Exception as e:
                    error_msg = f"Error processing paper: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
                    console.print(f"[red]{error_msg}[/red]")

            # Step 3: Generate articles and publish to Notion
            if successful_strategies:
                console.print(f"\n[cyan]Step 3: Publishing {len(successful_strategies)} strategies...[/cyan]")

                for strategy in successful_strategies:
                    try:
                        published = await self._publish_strategy(strategy)
                        if published:
                            result.strategies_published += 1
                            console.print(f"[green]Published: {strategy['name']}[/green]")
                    except Exception as e:
                        error_msg = f"Error publishing strategy: {e}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Pipeline error: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            console.print(f"[red]{error_msg}[/red]")

        result.completed_at = datetime.now()

        # Print summary
        self._print_summary(result)

        return result

    async def _discover_papers(self) -> List[Dict]:
        """Discover papers from configured search queries."""
        all_papers = []

        for query in self.pipeline_config.search_queries:
            try:
                # Use the autonomous pipeline's paper fetching
                papers = await self.autonomous._fetch_papers(
                    query,
                    limit=self.pipeline_config.papers_per_query
                )
                all_papers.extend(papers)
                console.print(f"  [dim]'{query}': {len(papers)} papers[/dim]")
            except Exception as e:
                logger.warning(f"Error fetching papers for '{query}': {e}")

        # Deduplicate by URL/DOI
        seen = set()
        unique_papers = []
        for paper in all_papers:
            identifier = paper.get('doi') or paper.get('url') or paper.get('title')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_papers.append(paper)

        return unique_papers

    async def _process_paper(self, paper: Dict) -> Optional[Dict]:
        """Process a single paper: generate strategy and backtest.

        Returns:
            Strategy result dict if successful, None otherwise
        """
        # Generate strategy using the autonomous pipeline's method
        enhanced_prompts = self.autonomous.prompt_refiner.get_enhanced_prompts_for_agents(
            strategy_type=self.autonomous._extract_strategy_type(paper.get('title', ''))
        )

        strategy = await self.autonomous._generate_strategy(paper, enhanced_prompts)

        if not strategy:
            return None

        # Validate
        validation_result = await self.autonomous._validate_and_learn(strategy, iteration=1)

        if not validation_result['valid']:
            # Try self-healing
            strategy = await self.autonomous._apply_learned_fixes(strategy, validation_result['errors'])
            validation_result = await self.autonomous._validate_and_learn(strategy, iteration=1)

            if not validation_result['valid']:
                logger.warning(f"Strategy validation failed for {paper.get('title', 'unknown')}")
                return None

        # Backtest
        backtest_result = await self.autonomous._backtest(strategy)

        # Build complete result
        return {
            'name': strategy['name'],
            'paper': paper,
            'code_files': strategy.get('code_files', {}),
            'code': strategy.get('code', ''),
            'backtest_results': backtest_result,
            'strategy_type': self.autonomous._extract_strategy_type(paper.get('title', ''))
        }

    async def _publish_strategy(self, strategy: Dict) -> bool:
        """Publish strategy to Notion and save locally.

        Returns:
            True if published successfully
        """
        paper = strategy['paper']
        backtest = strategy['backtest_results']

        # Create strategy report
        report = StrategyReport(
            strategy_name=strategy['name'],
            paper_title=paper.get('title', 'Unknown'),
            paper_url=paper.get('url', ''),
            paper_authors=paper.get('authors', []),
            paper_abstract=paper.get('abstract', ''),
            strategy_type=strategy['strategy_type'],
            strategy_summary='',  # Will be generated
            code_files=strategy.get('code_files', {}),
            backtest_results=backtest,
            quantconnect_project_id=backtest.get('project_id'),
            quantconnect_backtest_id=backtest.get('backtest_id')
        )

        # Save locally
        output_dir = self.pipeline_config.output_dir / strategy['name']

        if self.pipeline_config.save_markdown:
            self.article_generator.save_markdown(report, output_dir)

        if self.pipeline_config.save_json:
            self.article_generator.save_json_report(report, output_dir)

        # Save code files
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename, code in strategy.get('code_files', {}).items():
            if code:
                (output_dir / filename).write_text(code, encoding='utf-8')

        # Publish to Notion if configured and meets threshold
        if self.pipeline_config.publish_to_notion:
            sharpe = backtest.get('sharpe_ratio', 0)

            if sharpe >= self.pipeline_config.notion_min_sharpe:
                if self.notion.is_configured():
                    article = self.article_generator.generate_notion_article(report)
                    notion_page = self.notion.create_strategy_page(article)

                    if notion_page:
                        console.print(f"[green]Published to Notion: {notion_page.url}[/green]")
                        return True
                    else:
                        console.print("[yellow]Failed to publish to Notion[/yellow]")
                else:
                    console.print("[yellow]Notion not configured, skipping publish[/yellow]")
            else:
                console.print(f"[dim]Sharpe {sharpe:.2f} below Notion threshold ({self.pipeline_config.notion_min_sharpe})[/dim]")

        return True  # Local save counts as success

    def _print_summary(self, result: PipelineResult):
        """Print pipeline run summary."""
        from rich.table import Table

        console.print("\n" + "=" * 60)
        console.print("[bold cyan]Pipeline Run Complete[/bold cyan]")
        console.print("=" * 60 + "\n")

        table = Table(title="Run Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Run ID", result.run_id)
        table.add_row("Duration", str(result.duration) if result.duration else "N/A")
        table.add_row("Papers Found", str(result.papers_found))
        table.add_row("Papers Processed", str(result.papers_processed))
        table.add_row("Strategies Generated", str(result.strategies_generated))
        table.add_row("Passed Backtest", str(result.strategies_passed_backtest))
        table.add_row("Published to Notion", str(result.strategies_published))

        if result.best_strategy:
            table.add_row("Best Strategy", f"{result.best_strategy['name']} (Sharpe: {result.best_strategy['sharpe_ratio']:.2f})")

        console.print(table)

        if result.errors:
            console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for err in result.errors[:5]:
                console.print(f"  [red]- {err}[/red]")


async def run_automated_pipeline(
    config: Optional[Config] = None,
    pipeline_config: Optional[PipelineConfig] = None
) -> Dict[str, Any]:
    """Convenience function to run the automated pipeline.

    Returns:
        Dict with run statistics for the scheduler
    """
    pipeline = AutomatedBacktestPipeline(config=config, pipeline_config=pipeline_config)
    result = await pipeline.run()

    return {
        "strategies_generated": result.strategies_generated,
        "strategies_published": result.strategies_published,
        "success": len(result.errors) == 0,
        "result": result.to_dict()
    }
