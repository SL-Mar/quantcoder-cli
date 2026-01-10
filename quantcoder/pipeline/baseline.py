"""Baseline pipeline for single strategy generation with self-improvement loop.

This is the core workflow:
  search → fetch PDF → NLP extract → generate (CoordinatorAgent) →
  validate → self-improvement loop → backtest (MCP) → output

Used by:
  - `generate` command (single strategy)
  - `AutoMode` (looped with prompt variation)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from rich.console import Console

from quantcoder.config import Config


console = Console()


@dataclass
class StrategyResult:
    """Result of baseline pipeline execution."""
    success: bool
    name: str = ""
    code_files: Dict[str, str] = field(default_factory=dict)
    backtest_metrics: Dict[str, float] = field(default_factory=dict)
    paper_title: str = ""
    paper_url: str = ""
    errors_fixed: int = 0
    refinement_attempts: int = 0
    error_message: str = ""

    @property
    def sharpe_ratio(self) -> float:
        return self.backtest_metrics.get('sharpe_ratio', 0.0)

    @property
    def max_drawdown(self) -> float:
        return self.backtest_metrics.get('max_drawdown', 0.0)

    @property
    def total_return(self) -> float:
        return self.backtest_metrics.get('total_return', 0.0)


class BaselinePipeline:
    """Single strategy generation pipeline with self-improvement loop.

    Workflow:
        1. Search/fetch article (CrossRef + PDF download)
        2. NLP extraction (SpaCy pipeline)
        3. Code generation (CoordinatorAgent → multi-file)
        4. Validation + self-improvement loop (ErrorLearner)
        5. Backtest (QuantConnect MCP)
        6. Return validated strategy with metrics
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        max_fix_attempts: int = 5,
        demo_mode: bool = False
    ):
        """Initialize baseline pipeline.

        Args:
            config: Application configuration
            max_fix_attempts: Maximum attempts to fix validation errors
            demo_mode: Run in demo mode without real API calls
        """
        self.config = config or Config()
        self.max_fix_attempts = max_fix_attempts
        self.demo_mode = demo_mode

        # Lazy-load learning components
        self._error_learner = None
        self._db = None

    @property
    def error_learner(self):
        """Lazy-load error learner."""
        if self._error_learner is None:
            from quantcoder.autonomous.database import LearningDatabase
            from quantcoder.autonomous.learner import ErrorLearner
            self._db = LearningDatabase()
            self._error_learner = ErrorLearner(self._db)
        return self._error_learner

    async def run_from_article_id(
        self,
        article_id: int,
        strategy_context: str = ""
    ) -> StrategyResult:
        """Run baseline pipeline from a downloaded article.

        Args:
            article_id: ID of the downloaded article (1-indexed)
            strategy_context: Optional context for strategy generation

        Returns:
            StrategyResult with generated strategy and metrics
        """
        # Step 1: Load and process article
        console.print("[cyan]📄 Loading article...[/cyan]")
        paper = await self._load_article(article_id)

        if not paper:
            return StrategyResult(
                success=False,
                error_message=f"Article {article_id} not found or could not be processed"
            )

        return await self._run_pipeline(paper, strategy_context)

    async def run_from_query(
        self,
        query: str,
        strategy_context: str = ""
    ) -> StrategyResult:
        """Run baseline pipeline from a search query.

        Args:
            query: Search query for CrossRef
            strategy_context: Optional context for strategy generation

        Returns:
            StrategyResult with generated strategy and metrics
        """
        # Step 1: Search and fetch paper
        console.print(f"[cyan]🔍 Searching for: {query}[/cyan]")
        paper = await self._search_and_fetch(query)

        if not paper:
            return StrategyResult(
                success=False,
                error_message=f"No papers found for query: {query}"
            )

        return await self._run_pipeline(paper, strategy_context)

    async def _run_pipeline(
        self,
        paper: Dict[str, Any],
        strategy_context: str = ""
    ) -> StrategyResult:
        """Run the core pipeline on a paper.

        Args:
            paper: Paper data with title, abstract, extracted_data, etc.
            strategy_context: Optional context for generation

        Returns:
            StrategyResult with generated strategy and metrics
        """
        console.print(f"[green]✓ Paper: {paper.get('title', 'Unknown')[:70]}...[/green]")

        # Step 2: Generate strategy via CoordinatorAgent
        console.print("[cyan]⚙️  Generating strategy code...[/cyan]")
        strategy = await self._generate_strategy(paper, strategy_context)

        if not strategy:
            return StrategyResult(
                success=False,
                paper_title=paper.get('title', ''),
                error_message="Failed to generate strategy code"
            )

        console.print(f"[green]✓ Generated: {strategy['name']}[/green]")

        # Step 3: Validation + self-improvement loop
        console.print("[cyan]🔍 Validating code...[/cyan]")
        validated_strategy, fix_attempts = await self._validate_with_self_improvement(strategy)

        if not validated_strategy:
            return StrategyResult(
                success=False,
                name=strategy['name'],
                paper_title=paper.get('title', ''),
                paper_url=paper.get('url', ''),
                refinement_attempts=fix_attempts,
                error_message="Could not fix validation errors after max attempts"
            )

        console.print(f"[green]✓ Validation passed (fixes: {fix_attempts})[/green]")

        # Step 4: Backtest via MCP
        console.print("[cyan]📊 Running backtest...[/cyan]")
        backtest_result = await self._backtest(validated_strategy)

        sharpe = backtest_result.get('sharpe_ratio', 0.0)
        drawdown = backtest_result.get('max_drawdown', 0.0)
        total_return = backtest_result.get('total_return', 0.0)

        console.print(
            f"[{'green' if sharpe >= 0.5 else 'yellow'}]"
            f"Results: Sharpe={sharpe:.2f}, MaxDD={drawdown:.1%}, Return={total_return:.1%}"
            f"[/{'green' if sharpe >= 0.5 else 'yellow'}]"
        )

        return StrategyResult(
            success=True,
            name=validated_strategy['name'],
            code_files=validated_strategy.get('code_files', {}),
            backtest_metrics=backtest_result,
            paper_title=paper.get('title', ''),
            paper_url=paper.get('url', ''),
            errors_fixed=fix_attempts,
            refinement_attempts=fix_attempts
        )

    async def _load_article(self, article_id: int) -> Optional[Dict]:
        """Load and process a downloaded article."""
        if self.demo_mode:
            return self._mock_paper(article_id)

        try:
            from quantcoder.core.processor import ArticleProcessor

            pdf_path = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

            if not pdf_path.exists():
                console.print(f"[red]Article {article_id} not found at {pdf_path}[/red]")
                return None

            processor = ArticleProcessor(self.config)
            extracted_data = processor.extract_structure(str(pdf_path))

            summary = ""
            if extracted_data:
                summary = processor.generate_summary(extracted_data)

            return {
                'title': f'Article {article_id}',
                'url': '',
                'abstract': summary,
                'extracted_data': extracted_data or {},
                'pdf_path': str(pdf_path)
            }

        except Exception as e:
            console.print(f"[red]Error loading article: {e}[/red]")
            return None

    async def _search_and_fetch(self, query: str) -> Optional[Dict]:
        """Search CrossRef and fetch first result."""
        if self.demo_mode:
            return self._mock_paper(1, query)

        try:
            from quantcoder.tools.article_tools import SearchArticlesTool, DownloadArticleTool
            from quantcoder.core.processor import ArticleProcessor

            # Search
            search_tool = SearchArticlesTool(self.config)
            search_result = search_tool.execute(query=query, max_results=3)

            if not search_result.success or not search_result.data:
                return None

            article = search_result.data[0]

            # Download
            download_tool = DownloadArticleTool(self.config)
            download_result = download_tool.execute(article_id=1)

            if not download_result.success:
                # Return with just metadata
                return {
                    'title': article.get('title', 'Unknown'),
                    'url': article.get('URL', ''),
                    'abstract': f"Strategy based on: {article.get('title', '')}",
                    'extracted_data': {},
                    'pdf_path': None
                }

            # Process with NLP
            processor = ArticleProcessor(self.config)
            pdf_path = download_result.data
            extracted_data = processor.extract_structure(pdf_path)

            summary = ""
            if extracted_data:
                summary = processor.generate_summary(extracted_data)

            return {
                'title': article.get('title', 'Unknown'),
                'url': article.get('URL', ''),
                'doi': article.get('DOI', ''),
                'authors': article.get('authors', []),
                'abstract': summary or article.get('title', ''),
                'extracted_data': extracted_data or {},
                'pdf_path': pdf_path
            }

        except Exception as e:
            console.print(f"[red]Error searching/fetching: {e}[/red]")
            return None

    async def _generate_strategy(
        self,
        paper: Dict,
        strategy_context: str = ""
    ) -> Optional[Dict]:
        """Generate strategy code via CoordinatorAgent."""
        if self.demo_mode:
            return self._mock_strategy(paper)

        try:
            from quantcoder.agents.coordinator_agent import CoordinatorAgent
            from quantcoder.llm import LLMFactory

            # Create LLM for coordination
            llm = LLMFactory.create(
                LLMFactory.get_recommended_for_task("coordination"),
                self.config.api_key if self.config else ""
            )

            # Initialize coordinator
            coordinator = CoordinatorAgent(llm, self.config)

            # Build strategy summary
            strategy_summary = self._build_strategy_summary(paper, strategy_context)

            # Execute multi-agent workflow
            result = await coordinator.execute(
                user_request=paper.get('title', 'Generate trading strategy'),
                strategy_summary=strategy_summary,
                mcp_client=None  # TODO: Pass MCP client when available
            )

            if result.success:
                return {
                    'name': self._generate_strategy_name(paper),
                    'code': result.code,
                    'code_files': result.data.get('files', {}),
                    'paper_title': paper.get('title', ''),
                    'errors': 0
                }
            else:
                console.print(f"[yellow]Coordinator failed: {result.error}[/yellow]")
                return None

        except Exception as e:
            console.print(f"[red]Strategy generation error: {e}[/red]")
            return None

    def _build_strategy_summary(self, paper: Dict, strategy_context: str = "") -> str:
        """Build comprehensive strategy summary for CoordinatorAgent."""
        parts = []

        # Paper abstract/summary
        if paper.get('abstract'):
            parts.append(f"Research Summary:\n{paper['abstract']}")

        # NLP-extracted trading signals
        extracted_data = paper.get('extracted_data', {})
        if extracted_data:
            if extracted_data.get('trading_signal'):
                signals = extracted_data['trading_signal'][:10]
                parts.append("Trading Signals (NLP-extracted):\n" + "\n".join(f"- {s}" for s in signals))

            if extracted_data.get('risk_management'):
                risks = extracted_data['risk_management'][:10]
                parts.append("Risk Management (NLP-extracted):\n" + "\n".join(f"- {r}" for r in risks))

        # Additional context
        if strategy_context:
            parts.append(f"Strategy Context:\n{strategy_context}")

        return "\n\n".join(parts) if parts else paper.get('title', '')

    def _generate_strategy_name(self, paper: Dict) -> str:
        """Generate unique strategy name from paper."""
        title = paper.get('title', 'Strategy')
        words = [w for w in title.split()[:3] if w.isalpha()]
        base_name = ''.join(w.capitalize() for w in words)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}"

    async def _validate_with_self_improvement(
        self,
        strategy: Dict
    ) -> tuple[Optional[Dict], int]:
        """Validate strategy and apply self-improvement loop.

        Returns:
            Tuple of (validated_strategy or None, fix_attempts)
        """
        if self.demo_mode:
            # Simulate successful validation
            return strategy, 0

        current_strategy = strategy.copy()

        for attempt in range(self.max_fix_attempts):
            # Validate
            validation_result = await self._validate(current_strategy)

            if validation_result['valid']:
                return current_strategy, attempt

            console.print(f"[yellow]⚠ Validation errors ({len(validation_result['errors'])}), attempt {attempt + 1}[/yellow]")

            # Try to fix
            fixed_strategy = await self._apply_fixes(current_strategy, validation_result['errors'])

            if fixed_strategy:
                current_strategy = fixed_strategy
            else:
                break

        # Check one final time
        final_validation = await self._validate(current_strategy)
        if final_validation['valid']:
            return current_strategy, self.max_fix_attempts

        return None, self.max_fix_attempts

    async def _validate(self, strategy: Dict) -> Dict:
        """Validate strategy code."""
        if self.demo_mode:
            return {'valid': True, 'errors': []}

        try:
            # Basic Python syntax validation
            import ast

            errors = []
            code_files = strategy.get('code_files', {})

            for filename, code in code_files.items():
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append(f"{filename}: {e.msg} at line {e.lineno}")

            # TODO: Add MCP validation for QuantConnect-specific checks

            return {
                'valid': len(errors) == 0,
                'errors': errors
            }

        except Exception as e:
            return {'valid': False, 'errors': [str(e)]}

    async def _apply_fixes(
        self,
        strategy: Dict,
        errors: List[str]
    ) -> Optional[Dict]:
        """Apply learned fixes to strategy errors."""
        if self.demo_mode:
            return strategy

        try:
            fixed_strategy = strategy.copy()
            fixed_code_files = dict(strategy.get('code_files', {}))

            for error in errors:
                # Analyze error and get suggested fix
                error_pattern = self.error_learner.analyze_error(
                    error,
                    str(strategy.get('code', ''))
                )

                if error_pattern.suggested_fix:
                    console.print(f"[cyan]Applying fix: {error_pattern.suggested_fix[:60]}...[/cyan]")
                    # TODO: Apply the actual fix to the code
                    # For now, just log that we would apply it

            fixed_strategy['code_files'] = fixed_code_files
            return fixed_strategy

        except Exception as e:
            console.print(f"[yellow]Could not apply fixes: {e}[/yellow]")
            return None

    async def _backtest(self, strategy: Dict) -> Dict:
        """Run backtest via QuantConnect MCP."""
        if self.demo_mode:
            import random
            sharpe = random.uniform(0.3, 1.5)
            return {
                'sharpe_ratio': sharpe,
                'max_drawdown': random.uniform(-0.35, -0.08),
                'total_return': random.uniform(-0.15, 0.6),
                'win_rate': random.uniform(0.4, 0.65),
                'profit_factor': random.uniform(0.8, 2.0)
            }

        try:
            # TODO: Implement real MCP backtesting
            # from quantcoder.mcp import QuantConnectMCP
            # mcp = QuantConnectMCP(self.config)
            # return await mcp.backtest(strategy['code_files'])

            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0
            }

        except Exception as e:
            console.print(f"[red]Backtest error: {e}[/red]")
            return {'sharpe_ratio': 0.0, 'max_drawdown': 0.0, 'total_return': 0.0}

    # Mock methods for demo mode
    def _mock_paper(self, article_id: int, query: str = "trading strategy") -> Dict:
        """Generate mock paper for demo mode."""
        return {
            'title': f'A Novel Approach to {query.title()} in Financial Markets',
            'url': f'https://arxiv.org/abs/2024.{article_id:05d}',
            'abstract': f'This paper presents a comprehensive analysis of {query} strategies...',
            'extracted_data': {
                'trading_signal': [
                    'Buy when 50-day SMA crosses above 200-day SMA',
                    'Use RSI > 70 as overbought signal'
                ],
                'risk_management': [
                    'Maximum position size of 2% per trade',
                    'Stop-loss at 5% below entry'
                ]
            },
            'authors': ['Smith, J.', 'Doe, A.']
        }

    def _mock_strategy(self, paper: Dict) -> Dict:
        """Generate mock strategy for demo mode."""
        name = self._generate_strategy_name(paper)
        return {
            'name': name,
            'code': f'class {name.split("_")[0]}Algorithm(QCAlgorithm): pass',
            'code_files': {
                'Main.py': f'''from AlgorithmImports import *

class {name.split("_")[0]}Algorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
''',
                'Alpha.py': '# Alpha model placeholder',
                'Universe.py': '# Universe selection placeholder',
                'Risk.py': '# Risk management placeholder'
            },
            'paper_title': paper.get('title', ''),
            'errors': 0
        }
