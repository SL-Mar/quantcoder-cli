"""Coverage tracking for library building progress."""

from typing import Dict
from dataclasses import dataclass, field
from datetime import datetime
import time

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from quantcoder.library.taxonomy import STRATEGY_TAXONOMY, get_total_strategies_needed


console = Console()


@dataclass
class CategoryProgress:
    """Progress tracking for a single category."""
    category: str
    target: int
    completed: int = 0
    failed: int = 0
    avg_sharpe: float = 0.0
    best_sharpe: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def progress_pct(self) -> float:
        """Calculate progress percentage."""
        return (self.completed / self.target * 100) if self.target > 0 else 0

    @property
    def is_complete(self) -> bool:
        """Check if category target is met."""
        return self.completed >= self.target

    @property
    def elapsed_hours(self) -> float:
        """Calculate elapsed time in hours."""
        return (time.time() - self.start_time) / 3600


class CoverageTracker:
    """Track coverage and progress across all strategy categories."""

    def __init__(self):
        """Initialize coverage tracker."""
        self.categories: Dict[str, CategoryProgress] = {}
        self.start_time = time.time()
        self._initialize_categories()

    def _initialize_categories(self):
        """Initialize progress tracking for all categories."""
        for name, config in STRATEGY_TAXONOMY.items():
            self.categories[name] = CategoryProgress(
                category=name,
                target=config.min_strategies
            )

    def update(
        self,
        category: str,
        success: bool,
        sharpe: float = 0.0
    ):
        """Update progress for a category."""
        if category not in self.categories:
            return

        progress = self.categories[category]

        if success:
            progress.completed += 1

            # Update Sharpe statistics
            if sharpe > 0:
                if progress.avg_sharpe == 0:
                    progress.avg_sharpe = sharpe
                else:
                    progress.avg_sharpe = (
                        (progress.avg_sharpe * (progress.completed - 1) + sharpe) /
                        progress.completed
                    )

                if sharpe > progress.best_sharpe:
                    progress.best_sharpe = sharpe
        else:
            progress.failed += 1

    def get_progress_pct(self) -> float:
        """Get overall progress percentage."""
        total_target = sum(p.target for p in self.categories.values())
        total_completed = sum(p.completed for p in self.categories.values())
        return (total_completed / total_target * 100) if total_target > 0 else 0

    def get_completed_categories(self) -> int:
        """Get number of completed categories."""
        return sum(1 for p in self.categories.values() if p.is_complete)

    def get_total_strategies(self) -> int:
        """Get total strategies completed."""
        return sum(p.completed for p in self.categories.values())

    def get_elapsed_hours(self) -> float:
        """Get total elapsed time in hours."""
        return (time.time() - self.start_time) / 3600

    def estimate_time_remaining(self) -> float:
        """Estimate time remaining in hours."""
        total_target = sum(p.target for p in self.categories.values())
        total_completed = self.get_total_strategies()

        if total_completed == 0:
            return 0.0

        elapsed = self.get_elapsed_hours()
        rate = total_completed / elapsed  # strategies per hour
        remaining = total_target - total_completed

        return remaining / rate if rate > 0 else 0.0

    def get_progress_bar(self, category: str) -> str:
        """Get progress bar for a category."""
        if category not in self.categories:
            return ""

        progress = self.categories[category]
        pct = progress.progress_pct
        bar_width = 20
        filled = int(bar_width * pct / 100)
        empty = bar_width - filled

        bar = "█" * filled + "░" * empty
        status = "✓" if progress.is_complete else ""

        return f"{bar} {pct:5.1f}% {status}"

    def display_progress(self):
        """Display progress table."""
        table = Table(title="Library Build Progress")

        table.add_column("Category", style="cyan")
        table.add_column("Progress", style="green")
        table.add_column("Completed", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Avg Sharpe", justify="right")
        table.add_column("Best Sharpe", justify="right")

        # Sort by priority then completion
        priority_order = {"high": 0, "medium": 1, "low": 2}

        sorted_categories = sorted(
            self.categories.items(),
            key=lambda x: (
                priority_order.get(STRATEGY_TAXONOMY[x[0]].priority, 3),
                -x[1].progress_pct
            )
        )

        for name, progress in sorted_categories:
            table.add_row(
                name.replace("_", " ").title(),
                self.get_progress_bar(name),
                str(progress.completed),
                str(progress.target),
                f"{progress.avg_sharpe:.2f}" if progress.avg_sharpe > 0 else "-",
                f"{progress.best_sharpe:.2f}" if progress.best_sharpe > 0 else "-"
            )

        console.print(table)

        # Overall stats
        console.print(f"\n[bold]Overall Progress:[/bold]")
        console.print(f"  Total: {self.get_total_strategies()}/{get_total_strategies_needed()} "
                     f"({self.get_progress_pct():.1f}%)")
        console.print(f"  Completed categories: {self.get_completed_categories()}/{len(self.categories)}")
        console.print(f"  Elapsed time: {self.get_elapsed_hours():.1f} hours")

        remaining = self.estimate_time_remaining()
        if remaining > 0:
            console.print(f"  Estimated remaining: {remaining:.1f} hours")

    def get_status_report(self) -> Dict:
        """Get status report as dictionary."""
        return {
            'total_strategies': self.get_total_strategies(),
            'target_strategies': get_total_strategies_needed(),
            'progress_pct': self.get_progress_pct(),
            'completed_categories': self.get_completed_categories(),
            'total_categories': len(self.categories),
            'elapsed_hours': self.get_elapsed_hours(),
            'estimated_remaining_hours': self.estimate_time_remaining(),
            'categories': {
                name: {
                    'completed': p.completed,
                    'target': p.target,
                    'progress_pct': p.progress_pct,
                    'avg_sharpe': p.avg_sharpe,
                    'best_sharpe': p.best_sharpe,
                    'is_complete': p.is_complete
                }
                for name, p in self.categories.items()
            }
        }

    def save_checkpoint(self, filepath: str):
        """Save progress checkpoint."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.get_status_report(), f, indent=2)

    @classmethod
    def load_checkpoint(cls, filepath: str) -> 'CoverageTracker':
        """Load progress from checkpoint."""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)

        tracker = cls()

        # Restore category progress
        for name, cat_data in data.get('categories', {}).items():
            if name in tracker.categories:
                progress = tracker.categories[name]
                progress.completed = cat_data['completed']
                progress.avg_sharpe = cat_data['avg_sharpe']
                progress.best_sharpe = cat_data['best_sharpe']

        return tracker
