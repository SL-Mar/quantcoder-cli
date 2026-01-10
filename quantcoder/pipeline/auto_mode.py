"""Auto mode for autonomous library generation.

This module loops the BaselinePipeline N times with quant-perspective
prompt variation to generate a library of diverse strategies.

Workflow:
    for i in range(count):
        result = BaselinePipeline.run(current_prompt)
        analysis = QuantPerspectiveRefiner.analyze(result)
        next_prompt = QuantPerspectiveRefiner.suggest_next_prompt()
    output: library of N strategies
"""

import asyncio
import signal
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm

from quantcoder.config import Config
from quantcoder.pipeline.baseline import BaselinePipeline, StrategyResult
from quantcoder.pipeline.quant_refiner import QuantPerspectiveRefiner


console = Console()


@dataclass
class AutoModeStats:
    """Statistics for auto mode session."""
    total_attempts: int = 0
    successful: int = 0
    failed: int = 0
    total_sharpe: float = 0.0
    best_sharpe: float = 0.0
    best_strategy: str = ""
    start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful / self.total_attempts

    @property
    def avg_sharpe(self) -> float:
        if self.successful == 0:
            return 0.0
        return self.total_sharpe / self.successful

    @property
    def elapsed_hours(self) -> float:
        return (time.time() - self.start_time) / 3600


@dataclass
class LibraryEntry:
    """Entry in the strategy library."""
    name: str
    code_files: Dict[str, str]
    paper_title: str
    paper_url: str
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    query_used: str
    iteration: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AutoMode:
    """Autonomous library generation mode.

    Loops BaselinePipeline N times with quant-perspective prompt variation
    to generate a diverse library of strategies.

    Example:
        auto = AutoMode(config)
        library = await auto.run(
            query="momentum trading",
            count=10,
            min_sharpe=0.5
        )
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        demo_mode: bool = False
    ):
        """Initialize auto mode.

        Args:
            config: Application configuration
            demo_mode: Run in demo mode without real API calls
        """
        self.config = config or Config()
        self.demo_mode = demo_mode
        self.running = False

        # Initialize components
        self.baseline = BaselinePipeline(
            config=self.config,
            demo_mode=self.demo_mode
        )
        self.refiner = QuantPerspectiveRefiner()

        # Results
        self.results: List[StrategyResult] = []
        self.library: List[LibraryEntry] = []
        self.stats = AutoModeStats()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    async def run(
        self,
        query: str,
        count: int = 10,
        min_sharpe: float = 0.5,
        output_dir: Optional[Path] = None
    ) -> List[LibraryEntry]:
        """Run auto mode to generate library of strategies.

        Args:
            query: Base search query for strategy generation
            count: Number of strategies to generate (default: 10)
            min_sharpe: Minimum Sharpe ratio for successful strategies
            output_dir: Directory to save library

        Returns:
            List of LibraryEntry with generated strategies
        """
        self.running = True
        self.stats = AutoModeStats()
        self.results = []
        self.library = []

        if output_dir is None:
            output_dir = Path.cwd() / "strategy_library"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Display start panel
        console.print(Panel.fit(
            f"[bold cyan]Auto Mode - Library Generation[/bold cyan]\n\n"
            f"Base query: {query}\n"
            f"Target strategies: {count}\n"
            f"Min Sharpe: {min_sharpe}\n"
            f"Output: {output_dir}\n"
            f"Demo mode: {self.demo_mode}",
            title="🤖 Auto Mode"
        ))

        current_query = query
        iteration = 0

        while self.running and len(self.library) < count and iteration < count * 2:
            iteration += 1
            self.stats.total_attempts += 1

            console.print(f"\n{'=' * 80}")
            console.print(f"[bold]Iteration {iteration} | Library: {len(self.library)}/{count}[/bold]")
            console.print(f"[dim]Query: {current_query[:70]}...[/dim]")
            console.print(f"{'=' * 80}\n")

            try:
                # Run baseline pipeline
                result = await self.baseline.run_from_query(
                    query=current_query,
                    strategy_context=self.refiner.generate_strategy_context(query, self.results)
                )

                self.results.append(result)

                if result.success and result.sharpe_ratio >= min_sharpe:
                    self.stats.successful += 1
                    self.stats.total_sharpe += result.sharpe_ratio

                    # Update best
                    if result.sharpe_ratio > self.stats.best_sharpe:
                        self.stats.best_sharpe = result.sharpe_ratio
                        self.stats.best_strategy = result.name

                    # Add to library
                    entry = LibraryEntry(
                        name=result.name,
                        code_files=result.code_files,
                        paper_title=result.paper_title,
                        paper_url=result.paper_url,
                        sharpe_ratio=result.sharpe_ratio,
                        max_drawdown=result.max_drawdown,
                        total_return=result.total_return,
                        query_used=current_query,
                        iteration=iteration
                    )
                    self.library.append(entry)

                    # Save to disk
                    self._save_strategy(entry, output_dir)

                    console.print(
                        f"[green]✓ Added to library: {result.name} "
                        f"(Sharpe: {result.sharpe_ratio:.2f})[/green]"
                    )
                else:
                    self.stats.failed += 1
                    if result.success:
                        console.print(
                            f"[yellow]⚠ Below threshold: Sharpe {result.sharpe_ratio:.2f} < {min_sharpe}[/yellow]"
                        )
                    else:
                        console.print(f"[red]✗ Failed: {result.error_message}[/red]")

                # Analyze and refine prompt for next iteration
                analysis = self.refiner.analyze(result)
                current_query = self.refiner.suggest_next_prompt(query, result, analysis)

                # Display analysis insights
                if analysis.weaknesses:
                    console.print(f"[yellow]Analysis: {analysis.weaknesses[0]}[/yellow]")
                if analysis.priority_focus:
                    console.print(f"[cyan]Focus: {analysis.priority_focus}[/cyan]")

                # Progress update
                self._display_progress()

            except Exception as e:
                console.print(f"[red]Error in iteration {iteration}: {e}[/red]")
                self.stats.failed += 1

            # Check continuation
            if not await self._should_continue(iteration, count):
                break

        # Generate final report
        await self._generate_report(output_dir)

        console.print(f"\n[bold green]✓ Auto mode complete! Generated {len(self.library)} strategies[/bold green]")

        return self.library

    def _save_strategy(self, entry: LibraryEntry, output_dir: Path):
        """Save strategy to disk."""
        strategy_dir = output_dir / entry.name
        strategy_dir.mkdir(parents=True, exist_ok=True)

        # Save code files
        for filename, content in entry.code_files.items():
            filepath = strategy_dir / filename
            filepath.write_text(content)

        # Save metadata
        metadata = {
            'name': entry.name,
            'paper_title': entry.paper_title,
            'paper_url': entry.paper_url,
            'performance': {
                'sharpe_ratio': entry.sharpe_ratio,
                'max_drawdown': entry.max_drawdown,
                'total_return': entry.total_return
            },
            'query_used': entry.query_used,
            'iteration': entry.iteration,
            'created_at': entry.created_at
        }

        metadata_path = strategy_dir / 'metadata.json'
        metadata_path.write_text(json.dumps(metadata, indent=2))

    def _display_progress(self):
        """Display current progress."""
        table = Table(title="Session Progress", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Library size", str(len(self.library)))
        table.add_row("Attempts", str(self.stats.total_attempts))
        table.add_row("Success rate", f"{self.stats.success_rate:.1%}")
        table.add_row("Avg Sharpe", f"{self.stats.avg_sharpe:.2f}")
        if self.stats.best_strategy:
            table.add_row("Best", f"{self.stats.best_strategy} ({self.stats.best_sharpe:.2f})")

        console.print(table)

    async def _should_continue(self, iteration: int, target: int) -> bool:
        """Check if should continue running."""
        if not self.running:
            return False

        # Auto-continue in demo mode
        if self.demo_mode:
            return True

        # Ask every 5 iterations
        if iteration % 5 == 0 and len(self.library) < target:
            console.print(f"\n[dim]Library: {len(self.library)}/{target}[/dim]")
            response = Prompt.ask(
                "Continue?",
                choices=["y", "n"],
                default="y"
            )
            if response == "n":
                return False

        return True

    async def _generate_report(self, output_dir: Path):
        """Generate library report."""
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]Auto Mode Report[/bold cyan]")
        console.print("=" * 80)

        # Stats table
        table = Table(title="Session Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Attempts", str(self.stats.total_attempts))
        table.add_row("Library Size", str(len(self.library)))
        table.add_row("Success Rate", f"{self.stats.success_rate:.1%}")
        table.add_row("Average Sharpe", f"{self.stats.avg_sharpe:.2f}")
        table.add_row("Best Sharpe", f"{self.stats.best_sharpe:.2f}")
        table.add_row("Elapsed Time", f"{self.stats.elapsed_hours:.1f} hours")

        console.print(table)

        # Library summary
        if self.library:
            console.print("\n[bold cyan]Library Summary[/bold cyan]\n")
            lib_table = Table()
            lib_table.add_column("#", style="dim")
            lib_table.add_column("Strategy", style="cyan")
            lib_table.add_column("Sharpe", style="green")
            lib_table.add_column("MaxDD", style="red")
            lib_table.add_column("Return", style="blue")

            for i, entry in enumerate(sorted(self.library, key=lambda x: -x.sharpe_ratio), 1):
                lib_table.add_row(
                    str(i),
                    entry.name[:30],
                    f"{entry.sharpe_ratio:.2f}",
                    f"{entry.max_drawdown:.1%}",
                    f"{entry.total_return:.1%}"
                )

            console.print(lib_table)

        # Exploration summary
        exploration = self.refiner.get_exploration_summary()
        console.print(f"\n[bold cyan]Exploration Summary[/bold cyan]")
        console.print(f"Variations explored: {exploration['total_variations_explored']}")

        # Save library index
        self._save_library_index(output_dir)

    def _save_library_index(self, output_dir: Path):
        """Save library index file."""
        index = {
            'library_name': 'QuantCoder Strategy Library',
            'created_at': datetime.now().isoformat(),
            'stats': {
                'total_strategies': len(self.library),
                'total_attempts': self.stats.total_attempts,
                'success_rate': self.stats.success_rate,
                'avg_sharpe': self.stats.avg_sharpe,
                'best_sharpe': self.stats.best_sharpe,
                'elapsed_hours': self.stats.elapsed_hours
            },
            'strategies': [
                {
                    'name': e.name,
                    'sharpe_ratio': e.sharpe_ratio,
                    'max_drawdown': e.max_drawdown,
                    'total_return': e.total_return,
                    'paper_title': e.paper_title,
                    'query_used': e.query_used
                }
                for e in self.library
            ]
        }

        index_path = output_dir / 'index.json'
        index_path.write_text(json.dumps(index, indent=2))

        # Generate README
        readme = self._generate_readme(index)
        readme_path = output_dir / 'README.md'
        readme_path.write_text(readme)

        console.print(f"\n[green]✓ Library saved to {output_dir}[/green]")

    def _generate_readme(self, index: Dict) -> str:
        """Generate README for the library."""
        readme = f"""# QuantCoder Strategy Library

Generated on: {index['created_at']}
Build time: {index['stats']['elapsed_hours']:.1f} hours

## Overview

This library contains **{index['stats']['total_strategies']} algorithmic trading strategies**
generated autonomously by QuantCoder CLI using the Auto Mode.

## Performance Summary

| Metric | Value |
|--------|-------|
| Total Strategies | {index['stats']['total_strategies']} |
| Average Sharpe | {index['stats']['avg_sharpe']:.2f} |
| Best Sharpe | {index['stats']['best_sharpe']:.2f} |
| Success Rate | {index['stats']['success_rate']:.1%} |

## Strategies

"""
        for i, s in enumerate(sorted(index['strategies'], key=lambda x: -x['sharpe_ratio']), 1):
            readme += f"""### {i}. {s['name']}

- **Sharpe Ratio**: {s['sharpe_ratio']:.2f}
- **Max Drawdown**: {s['max_drawdown']:.1%}
- **Total Return**: {s['total_return']:.1%}
- **Based on**: {s['paper_title'][:60]}...

"""

        readme += """## Usage

Each strategy directory contains:
- `Main.py` - Main algorithm
- `Alpha.py` - Alpha model
- `Universe.py` - Universe selection
- `Risk.py` - Risk management
- `metadata.json` - Strategy metadata

## Disclaimer

All strategies have been backtested. Past performance does not guarantee future results.
Use at your own risk.

---
Generated by QuantCoder CLI
"""
        return readme

    def _handle_exit(self, signum, frame):
        """Handle graceful shutdown."""
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
        self.running = False
