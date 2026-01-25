"""Autonomous self-improving strategy generation pipeline."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

from quantcoder.autonomous.database import LearningDatabase, GeneratedStrategy
from quantcoder.autonomous.learner import ErrorLearner, PerformanceLearner
from quantcoder.autonomous.prompt_refiner import PromptRefiner
from quantcoder.config import Config

console = Console()


@dataclass
class AutoStats:
    """Statistics for autonomous mode session."""
    total_attempts: int = 0
    successful: int = 0
    failed: int = 0
    avg_sharpe: float = 0.0
    avg_refinement_attempts: float = 0.0
    auto_fix_rate: float = 0.0
    start_time: float = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful / self.total_attempts

    @property
    def elapsed_hours(self) -> float:
        """Calculate elapsed time in hours."""
        return (time.time() - self.start_time) / 3600


class AutonomousPipeline:
    """Self-improving autonomous strategy generation pipeline."""

    def __init__(
        self,
        config: Optional[Config] = None,
        demo_mode: bool = False,
        db_path: Optional[Path] = None
    ):
        """Initialize autonomous pipeline."""
        self.config = config or Config()
        self.demo_mode = demo_mode
        self.running = False
        self.paused = False

        # Initialize learning systems
        self.db = LearningDatabase(db_path)
        self.error_learner = ErrorLearner(self.db)
        self.perf_learner = PerformanceLearner(self.db)
        self.prompt_refiner = PromptRefiner(self.db)

        # Statistics
        self.stats = AutoStats()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    async def run(
        self,
        query: str,
        max_iterations: int = 50,
        min_sharpe: float = 0.5,
        output_dir: Optional[Path] = None
    ):
        """Run autonomous generation loop."""
        self.running = True
        self.stats = AutoStats()

        console.print(Panel.fit(
            f"[bold cyan]Autonomous Mode Started[/bold cyan]\n\n"
            f"Query: {query}\n"
            f"Max iterations: {max_iterations}\n"
            f"Min Sharpe: {min_sharpe}\n"
            f"Demo mode: {self.demo_mode}",
            title="🤖 Autonomous Pipeline"
        ))

        if output_dir is None:
            output_dir = Path.cwd() / "autonomous_strategies"
        output_dir.mkdir(parents=True, exist_ok=True)

        iteration = 0

        while self.running and iteration < max_iterations:
            iteration += 1

            console.print(f"\n{'=' * 80}")
            console.print(f"[bold]Iteration {iteration}/{max_iterations}[/bold]")
            console.print(f"{'=' * 80}\n")

            try:
                # Execute one iteration
                success = await self._run_iteration(
                    query=query,
                    iteration=iteration,
                    min_sharpe=min_sharpe,
                    output_dir=output_dir
                )

                if success:
                    self.stats.successful += 1
                else:
                    self.stats.failed += 1

                self.stats.total_attempts += 1

                # Check if we should continue
                if not await self._should_continue(iteration, max_iterations):
                    break

            except Exception as e:
                console.print(f"[red]Error in iteration {iteration}: {e}[/red]")
                self.stats.failed += 1
                self.stats.total_attempts += 1

        # Generate final report
        await self._generate_final_report()

    async def _run_iteration(
        self,
        query: str,
        iteration: int,
        min_sharpe: float,
        output_dir: Path
    ) -> bool:
        """Run a single iteration of strategy generation."""

        # Step 1: Fetch papers
        console.print("[cyan]📚 Fetching research papers...[/cyan]")
        papers = await self._fetch_papers(query, limit=5)

        if not papers:
            console.print("[yellow]No papers found, skipping iteration[/yellow]")
            return False

        paper = papers[0]  # Use first paper
        console.print(f"[green]✓ Found: {paper['title'][:80]}...[/green]")

        # Step 2: Get enhanced prompts with learnings
        console.print("[cyan]🧠 Applying learned patterns...[/cyan]")
        enhanced_prompts = self.prompt_refiner.get_enhanced_prompts_for_agents(
            strategy_type=self._extract_strategy_type(query)
        )

        # Step 3: Generate strategy
        console.print("[cyan]⚙️  Generating strategy code...[/cyan]")
        strategy = await self._generate_strategy(paper, enhanced_prompts)

        if not strategy:
            console.print("[red]✗ Failed to generate strategy[/red]")
            return False

        console.print(f"[green]✓ Generated: {strategy['name']}[/green]")

        # Step 4: Validate and learn from errors
        console.print("[cyan]🔍 Validating code...[/cyan]")
        validation_result = await self._validate_and_learn(strategy, iteration)

        if not validation_result['valid']:
            console.print(f"[yellow]⚠ Validation errors found ({validation_result['error_count']})[/yellow]")

            # Attempt self-healing
            console.print("[cyan]🔧 Attempting self-healing...[/cyan]")
            strategy = await self._apply_learned_fixes(strategy, validation_result['errors'])

            # Re-validate
            validation_result = await self._validate_and_learn(strategy, iteration)

            if not validation_result['valid']:
                console.print("[red]✗ Could not fix validation errors[/red]")
                self.stats.avg_refinement_attempts += validation_result.get('attempts', 0)
                return False
            else:
                console.print("[green]✓ Self-healing successful![/green]")
                self.stats.auto_fix_rate = (
                    (self.stats.auto_fix_rate * self.stats.total_attempts + 1) /
                    (self.stats.total_attempts + 1)
                )

        console.print("[green]✓ Validation passed[/green]")

        # Step 5: Backtest
        console.print("[cyan]📊 Running backtest...[/cyan]")
        backtest_result = await self._backtest(strategy)

        sharpe = backtest_result.get('sharpe_ratio', 0.0)
        drawdown = backtest_result.get('max_drawdown', 0.0)

        console.print(f"[cyan]Results: Sharpe={sharpe:.2f}, Drawdown={drawdown:.1%}[/cyan]")

        # Step 6: Learn from performance
        if sharpe < min_sharpe:
            console.print(f"[yellow]⚠ Below target Sharpe ({min_sharpe})[/yellow]")

            insights = self.perf_learner.analyze_poor_performance(
                strategy_code=str(strategy['code']),
                strategy_type=self._extract_strategy_type(query),
                sharpe=sharpe,
                drawdown=drawdown
            )

            console.print("[yellow]Issues identified:[/yellow]")
            for issue in insights['issues'][:3]:
                console.print(f"  • {issue}")

            success = False
        else:
            console.print(f"[green]✓ Success! Sharpe={sharpe:.2f}[/green]")

            self.perf_learner.identify_success_patterns(
                strategy_code=str(strategy['code']),
                strategy_type=self._extract_strategy_type(query),
                sharpe=sharpe,
                drawdown=drawdown
            )

            success = True

        # Step 7: Store strategy
        self._store_strategy(
            strategy=strategy,
            paper=paper,
            backtest_result=backtest_result,
            success=success,
            output_dir=output_dir
        )

        # Update stats
        self.stats.avg_sharpe = (
            (self.stats.avg_sharpe * self.stats.total_attempts + sharpe) /
            (self.stats.total_attempts + 1)
        )

        return success

    async def _fetch_papers(self, query: str, limit: int = 5) -> List[Dict]:
        """Fetch research papers."""
        if self.demo_mode:
            return self._mock_papers(query, limit)

        # TODO: Implement real arXiv/CrossRef fetching
        # For now, return mock data
        return self._mock_papers(query, limit)

    async def _generate_strategy(
        self,
        paper: Dict,
        enhanced_prompts: Dict[str, str]
    ) -> Optional[Dict]:
        """Generate strategy code."""
        if self.demo_mode:
            return self._mock_strategy(paper)

        # TODO: Integrate with real coordinator agent
        # For now, return mock strategy
        return self._mock_strategy(paper)

    async def _validate_and_learn(
        self,
        strategy: Dict,
        iteration: int
    ) -> Dict:
        """Validate strategy and learn from errors."""
        if self.demo_mode:
            # Simulate some errors in early iterations
            if iteration <= 3:
                return {
                    'valid': False,
                    'error_count': 2,
                    'errors': ['ImportError: No module named AlgorithmImports'],
                    'attempts': 1
                }
            return {'valid': True, 'error_count': 0, 'errors': []}

        # Use real validation via MCP
        from quantcoder.tools import ValidateCodeTool

        code = strategy.get('code', '')
        if not code and strategy.get('code_files'):
            code = strategy['code_files'].get('Main.py', '')

        tool = ValidateCodeTool(self.config)
        result = tool.execute(code=code, use_quantconnect=True)

        if result.success:
            return {'valid': True, 'error_count': 0, 'errors': [], 'attempts': 0}
        else:
            errors = []
            if result.data and result.data.get('errors'):
                errors = result.data['errors']
            elif result.error:
                errors = [result.error]

            # Learn from the error
            for error in errors:
                self.error_learner.analyze_error(error, code)

            return {
                'valid': False,
                'error_count': len(errors),
                'errors': errors,
                'attempts': 1
            }

    async def _apply_learned_fixes(
        self,
        strategy: Dict,
        errors: List[str]
    ) -> Dict:
        """Apply learned fixes to strategy."""
        fixed_strategy = strategy.copy()

        for error in errors:
            # Analyze error
            error_pattern = self.error_learner.analyze_error(error, str(strategy['code']))

            if error_pattern.suggested_fix:
                console.print(f"[cyan]Applying fix: {error_pattern.suggested_fix}[/cyan]")
                # In production, apply the fix to the code
                # For now, just mark as fixed
                fixed_strategy['fixed'] = True

        return fixed_strategy

    async def _backtest(self, strategy: Dict) -> Dict:
        """Run backtest."""
        if self.demo_mode:
            # Return mock results with some variance
            import random
            sharpe = random.uniform(0.2, 1.5)
            return {
                'sharpe_ratio': sharpe,
                'max_drawdown': random.uniform(-0.4, -0.1),
                'total_return': random.uniform(-0.2, 0.8)
            }

        # Check if QuantConnect credentials are available
        if not self.config.has_quantconnect_credentials():
            console.print("[yellow]QuantConnect credentials not configured, skipping real backtest[/yellow]")
            return {'sharpe_ratio': 0.0, 'max_drawdown': 0.0, 'total_return': 0.0}

        # Use real backtesting via MCP
        from quantcoder.tools import BacktestTool

        code = strategy.get('code', '')
        if not code and strategy.get('code_files'):
            code = strategy['code_files'].get('Main.py', '')

        tool = BacktestTool(self.config)
        result = tool.execute(
            code=code,
            start_date="2020-01-01",
            end_date="2024-01-01",
            name=strategy.get('name')
        )

        if result.success and result.data:
            return {
                'sharpe_ratio': result.data.get('sharpe_ratio', 0.0),
                'max_drawdown': result.data.get('statistics', {}).get('Max Drawdown', 0.0),
                'total_return': result.data.get('total_return', 0.0),
                'backtest_id': result.data.get('backtest_id'),
                'statistics': result.data.get('statistics', {})
            }
        else:
            console.print(f"[yellow]Backtest failed: {result.error}[/yellow]")
            return {'sharpe_ratio': 0.0, 'max_drawdown': 0.0, 'total_return': 0.0}

    def _store_strategy(
        self,
        strategy: Dict,
        paper: Dict,
        backtest_result: Dict,
        success: bool,
        output_dir: Path
    ):
        """Store strategy in database and filesystem."""
        gen_strategy = GeneratedStrategy(
            name=strategy['name'],
            category=self._extract_strategy_type(strategy.get('query', 'unknown')),
            paper_source=paper.get('url', ''),
            paper_title=paper.get('title', ''),
            code_files=strategy.get('code_files', {}),
            sharpe_ratio=backtest_result.get('sharpe_ratio'),
            max_drawdown=backtest_result.get('max_drawdown'),
            total_return=backtest_result.get('total_return'),
            compilation_errors=strategy.get('errors', 0),
            refinement_attempts=strategy.get('refinements', 0),
            success=success
        )

        self.db.add_strategy(gen_strategy)

        # Write to filesystem if successful
        if success:
            strategy_dir = output_dir / strategy['name']
            strategy_dir.mkdir(parents=True, exist_ok=True)
            # TODO: Write files

    async def _should_continue(
        self,
        iteration: int,
        max_iterations: int
    ) -> bool:
        """Check if pipeline should continue."""
        if not self.running:
            return False

        # Check pause
        if self.paused:
            console.print("[yellow]Pipeline paused. Press Enter to continue...[/yellow]")
            input()
            self.paused = False

        # Ask user every 10 iterations
        if iteration % 10 == 0 and iteration < max_iterations:
            response = Prompt.ask(
                "\nContinue autonomous mode?",
                choices=["y", "n", "p"],
                default="y"
            )

            if response == "n":
                return False
            elif response == "p":
                self.paused = True
                return await self._should_continue(iteration, max_iterations)

        return True

    async def _generate_final_report(self):
        """Generate final learning report."""
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]Autonomous Mode Complete[/bold cyan]")
        console.print("=" * 80 + "\n")

        # Statistics table
        table = Table(title="Session Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Attempts", str(self.stats.total_attempts))
        table.add_row("Successful", str(self.stats.successful))
        table.add_row("Failed", str(self.stats.failed))
        table.add_row("Success Rate", f"{self.stats.success_rate:.1%}")
        table.add_row("Avg Sharpe", f"{self.stats.avg_sharpe:.2f}")
        table.add_row("Auto-Fix Rate", f"{self.stats.auto_fix_rate:.1%}")
        table.add_row("Elapsed Time", f"{self.stats.elapsed_hours:.1f} hours")

        console.print(table)

        # Learning insights
        console.print("\n[bold cyan]🧠 Key Learnings:[/bold cyan]\n")

        common_errors = self.error_learner.get_common_errors(limit=5)
        if common_errors:
            console.print("[yellow]Most Common Errors:[/yellow]")
            for i, error in enumerate(common_errors, 1):
                fix_rate = (error['fixed_count'] / error['count'] * 100) if error['count'] > 0 else 0
                console.print(f"  {i}. {error['error_type']}: {error['count']} occurrences ({fix_rate:.0f}% fixed)")

        # Library stats
        lib_stats = self.db.get_library_stats()
        console.print(f"\n[bold cyan]📚 Library Stats:[/bold cyan]")
        console.print(f"  Total strategies: {lib_stats.get('total_strategies', 0)}")
        console.print(f"  Successful: {lib_stats.get('successful', 0)}")
        console.print(f"  Average Sharpe: {lib_stats.get('avg_sharpe', 0):.2f}")

    def _handle_exit(self, signum, frame):
        """Handle graceful shutdown."""
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
        self.running = False
        self.db.close()
        sys.exit(0)

    def _extract_strategy_type(self, text: str) -> str:
        """Extract strategy type from query or text."""
        text_lower = text.lower()
        if 'momentum' in text_lower or 'trend' in text_lower:
            return 'momentum'
        elif 'mean reversion' in text_lower or 'reversal' in text_lower:
            return 'mean_reversion'
        elif 'arbitrage' in text_lower or 'pairs' in text_lower:
            return 'statistical_arbitrage'
        elif 'factor' in text_lower or 'value' in text_lower or 'quality' in text_lower:
            return 'factor_based'
        elif 'volatility' in text_lower or 'vix' in text_lower:
            return 'volatility'
        elif 'machine learning' in text_lower or 'ml' in text_lower or 'ai' in text_lower:
            return 'ml_based'
        else:
            return 'unknown'

    # Mock methods for demo mode
    def _mock_papers(self, query: str, limit: int) -> List[Dict]:
        """Generate mock papers for demo mode."""
        return [
            {
                'title': f'A Novel Approach to {query.title()} Strategies in Financial Markets',
                'url': 'https://arxiv.org/abs/2024.12345',
                'abstract': f'This paper presents a comprehensive analysis of {query} strategies...',
                'authors': ['Smith, J.', 'Doe, A.']
            }
            for i in range(limit)
        ]

    def _mock_strategy(self, paper: Dict) -> Dict:
        """Generate mock strategy for demo mode."""
        return {
            'name': 'MomentumStrategy_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
            'code': 'class MomentumAlgorithm(QCAlgorithm): pass',
            'code_files': {
                'Main.py': '# Main algorithm code',
                'Alpha.py': '# Alpha model code',
            },
            'query': paper.get('title', '')
        }
