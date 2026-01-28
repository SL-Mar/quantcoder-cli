"""Scheduled runner for automated strategy generation."""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class ScheduleInterval(Enum):
    """Predefined schedule intervals."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


@dataclass
class ScheduleConfig:
    """Configuration for scheduled runs."""
    interval: ScheduleInterval = ScheduleInterval.DAILY
    cron_expression: Optional[str] = None  # For custom schedules
    hour: int = 6  # Default run at 6 AM for daily
    minute: int = 0
    day_of_week: str = "mon"  # For weekly runs
    timezone: str = "UTC"
    max_runs: Optional[int] = None  # None = unlimited
    enabled: bool = True

    def to_trigger(self):
        """Convert config to APScheduler trigger."""
        if self.interval == ScheduleInterval.CUSTOM and self.cron_expression:
            return CronTrigger.from_crontab(self.cron_expression, timezone=self.timezone)
        elif self.interval == ScheduleInterval.HOURLY:
            return IntervalTrigger(hours=1, timezone=self.timezone)
        elif self.interval == ScheduleInterval.DAILY:
            return CronTrigger(hour=self.hour, minute=self.minute, timezone=self.timezone)
        elif self.interval == ScheduleInterval.WEEKLY:
            return CronTrigger(
                day_of_week=self.day_of_week,
                hour=self.hour,
                minute=self.minute,
                timezone=self.timezone
            )
        else:
            return IntervalTrigger(hours=24, timezone=self.timezone)


@dataclass
class RunStats:
    """Statistics for scheduler runs."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    strategies_generated: int = 0
    strategies_published: int = 0
    last_run_time: Optional[datetime] = None
    last_run_success: bool = True
    errors: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs


class ScheduledRunner:
    """Manages scheduled execution of the automated pipeline."""

    def __init__(
        self,
        pipeline_func: Callable,
        schedule_config: Optional[ScheduleConfig] = None,
        state_file: Optional[Path] = None
    ):
        """Initialize scheduled runner.

        Args:
            pipeline_func: Async function to run on schedule
            schedule_config: Schedule configuration
            state_file: Path to persist state between runs
        """
        self.pipeline_func = pipeline_func
        self.config = schedule_config or ScheduleConfig()
        self.state_file = state_file or Path.home() / ".quantcoder" / "scheduler_state.json"

        self.scheduler = AsyncIOScheduler(timezone=self.config.timezone)
        self.stats = RunStats()
        self.running = False

        # Callbacks
        self.on_run_start: Optional[Callable] = None
        self.on_run_complete: Optional[Callable[[bool, Any], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        # Load persisted state
        self._load_state()

    def _load_state(self):
        """Load persisted state from file."""
        if self.state_file.exists():
            try:
                import json
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self.stats.total_runs = data.get("total_runs", 0)
                self.stats.successful_runs = data.get("successful_runs", 0)
                self.stats.failed_runs = data.get("failed_runs", 0)
                self.stats.strategies_generated = data.get("strategies_generated", 0)
                self.stats.strategies_published = data.get("strategies_published", 0)
                if data.get("last_run_time"):
                    self.stats.last_run_time = datetime.fromisoformat(data["last_run_time"])
                logger.info(f"Loaded scheduler state: {self.stats.total_runs} previous runs")
            except Exception as e:
                logger.warning(f"Could not load scheduler state: {e}")

    def _save_state(self):
        """Save state to file."""
        try:
            import json
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "total_runs": self.stats.total_runs,
                "successful_runs": self.stats.successful_runs,
                "failed_runs": self.stats.failed_runs,
                "strategies_generated": self.stats.strategies_generated,
                "strategies_published": self.stats.strategies_published,
                "last_run_time": self.stats.last_run_time.isoformat() if self.stats.last_run_time else None,
                "last_run_success": self.stats.last_run_success
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save scheduler state: {e}")

    async def _execute_run(self):
        """Execute a single scheduled run."""
        run_start = datetime.now()
        self.stats.total_runs += 1
        self.stats.last_run_time = run_start

        console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
        console.print(f"[bold cyan]Scheduled Run #{self.stats.total_runs}[/bold cyan]")
        console.print(f"[dim]Started: {run_start.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

        if self.on_run_start:
            self.on_run_start()

        try:
            # Execute the pipeline
            result = await self.pipeline_func()

            # Update stats from result
            if result:
                self.stats.strategies_generated += result.get("strategies_generated", 0)
                self.stats.strategies_published += result.get("strategies_published", 0)

            self.stats.successful_runs += 1
            self.stats.last_run_success = True

            elapsed = datetime.now() - run_start
            console.print(f"\n[green]Run #{self.stats.total_runs} completed successfully[/green]")
            console.print(f"[dim]Duration: {elapsed}[/dim]")

            if self.on_run_complete:
                self.on_run_complete(True, result)

        except Exception as e:
            self.stats.failed_runs += 1
            self.stats.last_run_success = False
            self.stats.errors.append({
                "time": run_start.isoformat(),
                "error": str(e)
            })

            logger.error(f"Scheduled run failed: {e}")
            console.print(f"\n[red]Run #{self.stats.total_runs} failed: {e}[/red]")

            if self.on_error:
                self.on_error(e)

            if self.on_run_complete:
                self.on_run_complete(False, None)

        finally:
            self._save_state()

            # Check if we've hit max runs
            if self.config.max_runs and self.stats.total_runs >= self.config.max_runs:
                console.print(f"\n[yellow]Reached maximum runs ({self.config.max_runs}). Stopping scheduler.[/yellow]")
                self.stop()

    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        if not self.config.enabled:
            logger.warning("Scheduler is disabled in configuration")
            return

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Add job to scheduler
        trigger = self.config.to_trigger()
        self.scheduler.add_job(
            self._execute_run,
            trigger=trigger,
            id="automated_pipeline",
            name="Automated Strategy Pipeline",
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.running = True

        # Calculate next run time
        job = self.scheduler.get_job("automated_pipeline")
        next_run = job.next_run_time if job else None

        console.print(f"\n[green]Scheduler started[/green]")
        console.print(f"[cyan]Schedule:[/cyan] {self.config.interval.value}")
        if next_run:
            console.print(f"[cyan]Next run:[/cyan] {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        console.print(f"[dim]Press Ctrl+C to stop[/dim]\n")

        logger.info(f"Scheduler started with {self.config.interval.value} schedule")

    def stop(self):
        """Stop the scheduler gracefully."""
        if not self.running:
            return

        console.print("\n[yellow]Stopping scheduler...[/yellow]")
        self.scheduler.shutdown(wait=True)
        self.running = False
        self._save_state()

        console.print("[green]Scheduler stopped[/green]")
        logger.info("Scheduler stopped")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        console.print("\n[yellow]Received shutdown signal[/yellow]")
        self.stop()
        sys.exit(0)

    async def run_once(self):
        """Run the pipeline once immediately (for testing)."""
        console.print("[cyan]Running pipeline once...[/cyan]")
        await self._execute_run()

    async def run_forever(self):
        """Run the scheduler indefinitely."""
        self.start()
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def get_status(self) -> dict:
        """Get current scheduler status."""
        job = self.scheduler.get_job("automated_pipeline") if self.running else None

        return {
            "running": self.running,
            "enabled": self.config.enabled,
            "schedule": self.config.interval.value,
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "stats": {
                "total_runs": self.stats.total_runs,
                "successful_runs": self.stats.successful_runs,
                "failed_runs": self.stats.failed_runs,
                "success_rate": f"{self.stats.success_rate:.1%}",
                "strategies_generated": self.stats.strategies_generated,
                "strategies_published": self.stats.strategies_published,
                "last_run": self.stats.last_run_time.isoformat() if self.stats.last_run_time else None,
                "last_run_success": self.stats.last_run_success
            }
        }

    def print_status(self):
        """Print scheduler status to console."""
        from rich.table import Table
        from rich.panel import Panel

        status = self.get_status()

        # Status panel
        status_text = f"""[bold]Running:[/bold] {'Yes' if status['running'] else 'No'}
[bold]Schedule:[/bold] {status['schedule']}
[bold]Next Run:[/bold] {status['next_run'] or 'Not scheduled'}"""

        console.print(Panel(status_text, title="Scheduler Status", border_style="cyan"))

        # Stats table
        table = Table(title="Run Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        stats = status['stats']
        table.add_row("Total Runs", str(stats['total_runs']))
        table.add_row("Successful", str(stats['successful_runs']))
        table.add_row("Failed", str(stats['failed_runs']))
        table.add_row("Success Rate", stats['success_rate'])
        table.add_row("Strategies Generated", str(stats['strategies_generated']))
        table.add_row("Strategies Published", str(stats['strategies_published']))
        table.add_row("Last Run", stats['last_run'] or "Never")

        console.print(table)
