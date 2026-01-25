"""Library builder for creating comprehensive strategy library from scratch."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from quantcoder.library.taxonomy import (
    STRATEGY_TAXONOMY,
    get_categories_by_priority,
    get_total_strategies_needed,
    estimate_time_hours
)
from quantcoder.library.coverage import CoverageTracker
from quantcoder.autonomous.pipeline import AutonomousPipeline
from quantcoder.autonomous.database import LearningDatabase
from quantcoder.config import Config


console = Console()


class LibraryBuilder:
    """Build a comprehensive strategy library from scratch."""

    def __init__(
        self,
        config: Optional[Config] = None,
        demo_mode: bool = False
    ):
        """Initialize library builder."""
        self.config = config or Config()
        self.demo_mode = demo_mode
        self.running = False

        # Initialize tracking
        self.coverage = CoverageTracker()

        # Checkpoint file
        self.checkpoint_file = Path.home() / ".quantcoder" / "library_checkpoint.json"
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    async def build(
        self,
        comprehensive: bool = True,
        max_hours: int = 24,
        output_dir: Optional[Path] = None,
        min_sharpe: float = 0.5,
        categories: Optional[List[str]] = None
    ):
        """Build strategy library."""
        self.running = True

        if output_dir is None:
            output_dir = Path.cwd() / "strategies_library"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Display build plan
        self._display_build_plan(comprehensive, max_hours, categories)

        # Confirm start
        if not self.demo_mode:
            if not Confirm.ask("\nStart library build?"):
                console.print("[yellow]Build cancelled[/yellow]")
                return

        console.print("\n[bold green]Starting library build...[/bold green]\n")

        # Check for checkpoint
        if self.checkpoint_file.exists():
            if Confirm.ask("Resume from checkpoint?"):
                self.coverage = CoverageTracker.load_checkpoint(str(self.checkpoint_file))
                console.print("[green]Checkpoint loaded[/green]")

        start_time = datetime.now()
        max_seconds = max_hours * 3600

        # Determine which categories to build
        if categories:
            # Build specific categories
            target_categories = {
                name: cat for name, cat in STRATEGY_TAXONOMY.items()
                if name in categories
            }
        else:
            # Build all categories
            target_categories = STRATEGY_TAXONOMY

        # Process by priority
        for priority in ["high", "medium", "low"]:
            if not self.running:
                break

            priority_cats = {
                name: cat for name, cat in target_categories.items()
                if cat.priority == priority
            }

            if not priority_cats:
                continue

            console.print(f"\n[bold cyan]Building {priority.upper()} priority categories[/bold cyan]\n")

            for category_name, category_config in priority_cats.items():
                if not self.running:
                    break

                # Check time limit
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= max_seconds:
                    console.print("[yellow]Time limit reached[/yellow]")
                    self.running = False
                    break

                # Check if category is already complete
                if self.coverage.categories[category_name].is_complete:
                    console.print(f"[green]✓ {category_name} already complete, skipping[/green]")
                    continue

                # Build category
                await self._build_category(
                    category_name=category_name,
                    category_config=category_config,
                    min_sharpe=min_sharpe,
                    output_dir=output_dir
                )

                # Save checkpoint
                self.coverage.save_checkpoint(str(self.checkpoint_file))

                # Display progress
                console.print("\n")
                self.coverage.display_progress()

        # Generate final library report
        await self._generate_library_report(output_dir)

        console.print(f"\n[bold green]Library build complete![/bold green]")
        console.print(f"Output: {output_dir}")

    async def _build_category(
        self,
        category_name: str,
        category_config,
        min_sharpe: float,
        output_dir: Path
    ):
        """Build strategies for one category."""
        console.print(f"\n[bold cyan]Building: {category_name.replace('_', ' ').title()}[/bold cyan]")
        console.print(f"Target: {category_config.min_strategies} strategies\n")

        category_dir = output_dir / category_name
        category_dir.mkdir(parents=True, exist_ok=True)

        # Use autonomous pipeline for each query
        pipeline = AutonomousPipeline(
            config=self.config,
            demo_mode=self.demo_mode
        )

        strategies_needed = category_config.min_strategies
        strategies_built = self.coverage.categories[category_name].completed

        for query in category_config.queries:
            if not self.running:
                break

            if strategies_built >= strategies_needed:
                console.print(f"[green]✓ Category target reached ({strategies_built}/{strategies_needed})[/green]")
                break

            console.print(f"[cyan]Query: {query}[/cyan]")

            # Run autonomous pipeline for this query
            # Generate multiple strategies from this query
            attempts_per_query = min(5, strategies_needed - strategies_built)

            for i in range(attempts_per_query):
                if not self.running or strategies_built >= strategies_needed:
                    break

                console.print(f"  Attempt {i + 1}/{attempts_per_query}...")

                # Generate one strategy
                success, sharpe = await self._generate_one_strategy(
                    pipeline=pipeline,
                    query=query,
                    category=category_name,
                    min_sharpe=min_sharpe,
                    output_dir=category_dir
                )

                # Update coverage
                self.coverage.update(
                    category=category_name,
                    success=success,
                    sharpe=sharpe if success else 0.0
                )

                if success:
                    strategies_built += 1
                    console.print(f"    [green]✓ Success! Sharpe: {sharpe:.2f}[/green]")
                else:
                    console.print(f"    [red]✗ Failed[/red]")

    async def _generate_one_strategy(
        self,
        pipeline: AutonomousPipeline,
        query: str,
        category: str,
        min_sharpe: float,
        output_dir: Path
    ) -> tuple[bool, float]:
        """Generate a single strategy."""
        try:
            # Fetch papers
            papers = await pipeline._fetch_papers(query, limit=3)
            if not papers:
                return False, 0.0

            # Get enhanced prompts
            enhanced_prompts = pipeline.prompt_refiner.get_enhanced_prompts_for_agents(
                strategy_type=category
            )

            # Generate strategy
            strategy = await pipeline._generate_strategy(papers[0], enhanced_prompts)
            if not strategy:
                return False, 0.0

            # Validate
            validation = await pipeline._validate_and_learn(strategy, iteration=1)
            if not validation['valid']:
                # Try to fix
                strategy = await pipeline._apply_learned_fixes(strategy, validation.get('errors', []))
                validation = await pipeline._validate_and_learn(strategy, iteration=2)

                if not validation['valid']:
                    return False, 0.0

            # Backtest
            result = await pipeline._backtest(strategy)
            sharpe = result.get('sharpe_ratio', 0.0)

            # Check if meets threshold
            if sharpe < min_sharpe:
                return False, sharpe

            # Store strategy
            self._save_strategy_to_library(
                strategy=strategy,
                paper=papers[0],
                result=result,
                category=category,
                output_dir=output_dir
            )

            return True, sharpe

        except Exception as e:
            console.print(f"    [red]Error: {e}[/red]")
            return False, 0.0

    def _save_strategy_to_library(
        self,
        strategy: Dict,
        paper: Dict,
        result: Dict,
        category: str,
        output_dir: Path
    ):
        """Save strategy to library filesystem."""
        strategy_name = strategy['name']
        strategy_dir = output_dir / strategy_name
        strategy_dir.mkdir(parents=True, exist_ok=True)

        # Save code files
        code_files = strategy.get('code_files', {})
        for filename, content in code_files.items():
            filepath = strategy_dir / filename
            filepath.write_text(content)

        # Save metadata
        metadata = {
            'name': strategy_name,
            'category': category,
            'paper': {
                'title': paper.get('title', ''),
                'url': paper.get('url', ''),
                'authors': paper.get('authors', [])
            },
            'performance': {
                'sharpe_ratio': result.get('sharpe_ratio'),
                'max_drawdown': result.get('max_drawdown'),
                'total_return': result.get('total_return')
            },
            'created_at': datetime.now().isoformat()
        }

        metadata_file = strategy_dir / 'metadata.json'
        metadata_file.write_text(json.dumps(metadata, indent=2))

    async def _generate_library_report(self, output_dir: Path):
        """Generate comprehensive library report."""
        console.print("\n[bold cyan]Generating library report...[/bold cyan]")

        # Create index
        index = {
            'library_name': 'QuantCoder Strategy Library',
            'created_at': datetime.now().isoformat(),
            'total_strategies': self.coverage.get_total_strategies(),
            'target_strategies': get_total_strategies_needed(),
            'build_hours': self.coverage.get_elapsed_hours(),
            'categories': {}
        }

        # Add category details
        for category_name, progress in self.coverage.categories.items():
            index['categories'][category_name] = {
                'completed': progress.completed,
                'target': progress.target,
                'avg_sharpe': progress.avg_sharpe,
                'best_sharpe': progress.best_sharpe,
                'progress_pct': progress.progress_pct
            }

        # Save index
        index_file = output_dir / 'index.json'
        index_file.write_text(json.dumps(index, indent=2))

        # Generate README
        readme = self._generate_readme(index)
        readme_file = output_dir / 'README.md'
        readme_file.write_text(readme)

        console.print(f"[green]✓ Library report saved to {output_dir}[/green]")

    def _generate_readme(self, index: Dict) -> str:
        """Generate README for the library."""
        readme = f"""# QuantCoder Strategy Library

Generated on: {index['created_at']}
Build time: {index['build_hours']:.1f} hours

## Overview

This library contains **{index['total_strategies']} algorithmic trading strategies**
across {len(index['categories'])} categories, generated autonomously by QuantCoder CLI.

## Categories

"""
        # Add category sections
        for category, stats in index['categories'].items():
            if stats['completed'] == 0:
                continue

            readme += f"\n### {category.replace('_', ' ').title()}\n\n"
            readme += f"- Strategies: {stats['completed']}/{stats['target']}\n"
            readme += f"- Average Sharpe: {stats['avg_sharpe']:.2f}\n"
            readme += f"- Best Sharpe: {stats['best_sharpe']:.2f}\n"
            readme += f"- Progress: {stats['progress_pct']:.1f}%\n"

        readme += f"""

## Usage

Each strategy directory contains:
- `Main.py` - Main algorithm
- `Alpha.py` - Alpha model (if applicable)
- `Universe.py` - Universe selection (if applicable)
- `Risk.py` - Risk management (if applicable)
- `metadata.json` - Strategy metadata and performance

## Performance Note

All strategies have been backtested with Sharpe ratio >= 0.5.
Past performance does not guarantee future results.

## License

Generated by QuantCoder CLI
"""

        return readme

    def _display_build_plan(
        self,
        comprehensive: bool,
        max_hours: int,
        categories: Optional[List[str]]
    ):
        """Display build plan before starting."""
        console.print(Panel.fit(
            f"[bold cyan]Library Builder - Build Plan[/bold cyan]\n\n"
            f"Mode: {'Comprehensive' if comprehensive else 'Selective'}\n"
            f"Max time: {max_hours} hours\n"
            f"Categories: {len(categories) if categories else 'All (' + str(len(STRATEGY_TAXONOMY)) + ')'}\n"
            f"Target strategies: {get_total_strategies_needed() if comprehensive else 'Variable'}\n"
            f"Estimated time: {estimate_time_hours():.1f} hours\n"
            f"Demo mode: {self.demo_mode}",
            title="🏗️  Library Builder"
        ))

        # Show categories to build
        if categories:
            console.print("\n[bold]Categories to build:[/bold]")
            for cat in categories:
                if cat in STRATEGY_TAXONOMY:
                    config = STRATEGY_TAXONOMY[cat]
                    console.print(f"  • {cat}: {config.min_strategies} strategies ({config.priority} priority)")
        else:
            console.print("\n[bold]Building all categories:[/bold]")
            for name, config in STRATEGY_TAXONOMY.items():
                console.print(f"  • {name}: {config.min_strategies} strategies ({config.priority} priority)")

    def _handle_exit(self, signum, frame):
        """Handle graceful shutdown."""
        console.print("\n[yellow]Stopping library build gracefully...[/yellow]")
        self.running = False

        # Save checkpoint
        if hasattr(self, 'coverage'):
            self.coverage.save_checkpoint(str(self.checkpoint_file))
            console.print("[green]Progress saved to checkpoint[/green]")

        sys.exit(0)

    async def status(self):
        """Show current library build status."""
        if not self.checkpoint_file.exists():
            console.print("[yellow]No library build in progress[/yellow]")
            return

        self.coverage = CoverageTracker.load_checkpoint(str(self.checkpoint_file))
        console.print("\n[bold cyan]Library Build Status[/bold cyan]\n")
        self.coverage.display_progress()

    async def resume(self):
        """Resume library build from checkpoint."""
        if not self.checkpoint_file.exists():
            console.print("[yellow]No checkpoint found to resume from[/yellow]")
            return

        console.print("[cyan]Resuming from checkpoint...[/cyan]")
        # Load checkpoint and continue build
        await self.build(comprehensive=True)

    async def export(self, format: str = "zip", output_file: Optional[Path] = None):
        """Export library in specified format."""
        library_dir = Path.cwd() / "strategies_library"

        if not library_dir.exists():
            console.print("[red]No library found to export[/red]")
            return

        if format == "zip":
            if output_file is None:
                output_file = Path.cwd() / f"strategies_library_{datetime.now():%Y%m%d_%H%M%S}.zip"

            shutil.make_archive(
                str(output_file.with_suffix('')),
                'zip',
                library_dir
            )
            console.print(f"[green]✓ Library exported to {output_file}[/green]")

        elif format == "json":
            # Export as consolidated JSON
            if output_file is None:
                output_file = Path.cwd() / f"strategies_library_{datetime.now():%Y%m%d_%H%M%S}.json"

            index_file = library_dir / 'index.json'
            if index_file.exists():
                shutil.copy(index_file, output_file)
                console.print(f"[green]✓ Index exported to {output_file}[/green]")

        elif format == "html":
            console.print("[yellow]HTML export not yet implemented[/yellow]")
