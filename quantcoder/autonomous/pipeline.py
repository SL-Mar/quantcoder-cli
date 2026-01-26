"""Autonomous self-improving strategy generation pipeline."""

import asyncio
import ast
import json
import signal
import sys
import aiohttp
from pathlib import Path
from typing import Optional, Dict, List, Any
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
from quantcoder.agents.coordinator_agent import CoordinatorAgent
from quantcoder.llm import LLMFactory
from quantcoder.mcp.quantconnect_mcp import QuantConnectMCPClient

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

        # Initialize LLM and agents for real mode
        if not demo_mode:
            self._init_agents()
            self._init_mcp_client()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _init_agents(self):
        """Initialize LLM and coordinator agent."""
        try:
            # Get API key from config or environment
            api_key = self.config.api_key if hasattr(self.config, 'api_key') else None
            if not api_key:
                import os
                api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY', '')

            # Create LLM provider
            provider_name = LLMFactory.get_recommended_for_task("coding")
            self.llm = LLMFactory.create(provider_name, api_key)
            self.coordinator = CoordinatorAgent(self.llm, self.config)
            console.print("[green]✓ Coordinator agent initialized[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not initialize agents: {e}[/yellow]")
            self.llm = None
            self.coordinator = None

    def _init_mcp_client(self):
        """Initialize QuantConnect MCP client."""
        try:
            import os
            qc_api_key = os.getenv('QC_API_KEY', '')
            qc_user_id = os.getenv('QC_USER_ID', '')

            if qc_api_key and qc_user_id:
                self.mcp_client = QuantConnectMCPClient(qc_api_key, qc_user_id)
                console.print("[green]✓ QuantConnect MCP client initialized[/green]")
            else:
                self.mcp_client = None
                console.print("[yellow]⚠ QC_API_KEY/QC_USER_ID not set - backtesting disabled[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not initialize MCP client: {e}[/yellow]")
            self.mcp_client = None

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
        """Fetch research papers from arXiv and CrossRef APIs."""
        if self.demo_mode:
            return self._mock_papers(query, limit)

        papers = []

        # Try arXiv first (best for quantitative finance research)
        arxiv_papers = await self._fetch_from_arxiv(query, limit)
        papers.extend(arxiv_papers)

        # Supplement with CrossRef if needed
        if len(papers) < limit:
            crossref_papers = await self._fetch_from_crossref(query, limit - len(papers))
            papers.extend(crossref_papers)

        # Fall back to mock if APIs fail
        if not papers:
            console.print("[yellow]⚠ API fetch failed, using fallback[/yellow]")
            return self._mock_papers(query, limit)

        return papers[:limit]

    async def _fetch_from_arxiv(self, query: str, limit: int) -> List[Dict]:
        """Fetch papers from arXiv API."""
        try:
            # arXiv API for quantitative finance papers
            base_url = "http://export.arxiv.org/api/query"
            # Search in q-fin (quantitative finance) category
            search_query = f"all:{query} AND (cat:q-fin.* OR cat:stat.ML)"
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }

            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(base_url, params=params) as response:
                    response.raise_for_status()
                    content = await response.read()

            # Parse Atom XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)

            # Define namespaces
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            papers = []
            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                link_elem = entry.find("atom:link[@type='text/html']", ns)
                if link_elem is None:
                    link_elem = entry.find("atom:link[@rel='alternate']", ns)

                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None:
                        authors.append(name_elem.text)

                paper = {
                    'title': title_elem.text.strip().replace('\n', ' ') if title_elem is not None else 'Unknown',
                    'url': link_elem.get('href') if link_elem is not None else '',
                    'abstract': summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else '',
                    'authors': authors[:3],
                    'source': 'arxiv'
                }
                papers.append(paper)

            console.print(f"[green]✓ Found {len(papers)} papers from arXiv[/green]")
            return papers

        except Exception as e:
            console.print(f"[yellow]⚠ arXiv fetch failed: {e}[/yellow]")
            return []

    async def _fetch_from_crossref(self, query: str, limit: int) -> List[Dict]:
        """Fetch papers from CrossRef API."""
        try:
            api_url = "https://api.crossref.org/works"
            params = {
                "query": f"{query} trading strategy finance",
                "rows": limit,
                "select": "DOI,title,author,published-print,URL,abstract"
            }
            headers = {
                "User-Agent": "QuantCoder/2.0 (mailto:quantcoder@example.com)"
            }

            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, params=params, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

            papers = []
            for item in data.get('message', {}).get('items', []):
                title_list = item.get('title', ['Unknown'])
                title = title_list[0] if title_list else 'Unknown'

                authors = []
                for author in item.get('author', [])[:3]:
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if name:
                        authors.append(name)

                paper = {
                    'title': title,
                    'url': item.get('URL', ''),
                    'abstract': item.get('abstract', '')[:500] if item.get('abstract') else '',
                    'authors': authors,
                    'doi': item.get('DOI', ''),
                    'source': 'crossref'
                }
                papers.append(paper)

            console.print(f"[green]✓ Found {len(papers)} papers from CrossRef[/green]")
            return papers

        except Exception as e:
            console.print(f"[yellow]⚠ CrossRef fetch failed: {e}[/yellow]")
            return []

    async def _generate_strategy(
        self,
        paper: Dict,
        enhanced_prompts: Dict[str, str]
    ) -> Optional[Dict]:
        """Generate strategy code using the CoordinatorAgent."""
        if self.demo_mode:
            return self._mock_strategy(paper)

        if self.coordinator is None:
            console.print("[yellow]⚠ Coordinator not initialized, using fallback[/yellow]")
            return self._mock_strategy(paper)

        try:
            # Build user request from paper content
            paper_title = paper.get('title', 'Unknown Strategy')
            paper_abstract = paper.get('abstract', '')

            # Create strategy request combining paper info and enhanced prompts
            user_request = f"""Generate a QuantConnect trading algorithm based on this research:

Title: {paper_title}

Abstract: {paper_abstract}

Additional guidance from learned patterns:
{json.dumps(enhanced_prompts, indent=2) if enhanced_prompts else 'None'}

Create a complete, compilable algorithm with proper Universe selection, Alpha model, and Risk management."""

            # Use coordinator agent to generate strategy
            result = await self.coordinator.execute(
                user_request=user_request,
                strategy_summary=paper_abstract,
                mcp_client=self.mcp_client
            )

            if not result.success:
                console.print(f"[red]✗ Strategy generation failed: {result.error}[/red]")
                return None

            # Extract generated files from result
            files = result.data.get('files', {}) if result.data else {}

            strategy_name = self._generate_strategy_name(paper_title)

            return {
                'name': strategy_name,
                'code': result.code or files.get('Main.py', ''),
                'code_files': files,
                'query': paper_title,
                'paper_abstract': paper_abstract,
                'errors': 0,
                'refinements': 0
            }

        except Exception as e:
            console.print(f"[red]✗ Strategy generation error: {e}[/red]")
            return None

    def _generate_strategy_name(self, paper_title: str) -> str:
        """Generate a valid strategy name from paper title."""
        import re
        # Extract key words from title
        words = re.findall(r'\b[A-Za-z]+\b', paper_title)
        # Take first few meaningful words
        key_words = [w.capitalize() for w in words[:3] if len(w) > 2]
        if not key_words:
            key_words = ['Strategy']
        name = ''.join(key_words) + '_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        return name

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

        errors = []
        code_files = strategy.get('code_files', {})
        main_code = strategy.get('code', '') or code_files.get('Main.py', '')

        # Step 1: Local syntax validation using AST
        for filename, code in code_files.items():
            if filename.endswith('.py') and code:
                syntax_errors = self._validate_syntax(code, filename)
                errors.extend(syntax_errors)

        if main_code and 'Main.py' not in code_files:
            syntax_errors = self._validate_syntax(main_code, 'Main.py')
            errors.extend(syntax_errors)

        # Step 2: QuantConnect-specific validation
        qc_errors = self._validate_quantconnect_code(main_code, code_files)
        errors.extend(qc_errors)

        # Step 3: Use MCP client for remote validation if available
        if self.mcp_client and not errors:
            try:
                mcp_result = await self.mcp_client.validate_code(
                    code=main_code,
                    files={k: v for k, v in code_files.items() if k != 'Main.py'}
                )
                if not mcp_result.get('valid', True):
                    errors.extend(mcp_result.get('errors', []))
            except Exception as e:
                console.print(f"[yellow]⚠ MCP validation skipped: {e}[/yellow]")

        # Learn from errors
        for error in errors:
            self.error_learner.analyze_error(error, main_code)

        return {
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'errors': errors,
            'attempts': 1
        }

    def _validate_syntax(self, code: str, filename: str) -> List[str]:
        """Validate Python syntax using AST."""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"SyntaxError in {filename} line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"ValidationError in {filename}: {str(e)}")
        return errors

    def _validate_quantconnect_code(self, main_code: str, code_files: Dict[str, str]) -> List[str]:
        """Validate QuantConnect-specific patterns."""
        errors = []
        all_code = main_code + '\n'.join(code_files.values())

        # Check for required QuantConnect patterns
        required_patterns = [
            ('QCAlgorithm', 'Missing QCAlgorithm base class'),
            ('Initialize', 'Missing Initialize method'),
        ]

        for pattern, error_msg in required_patterns:
            if pattern not in all_code:
                errors.append(error_msg)

        # Check for common issues
        if 'from AlgorithmImports import *' not in all_code and 'from QuantConnect' not in all_code:
            if 'QCAlgorithm' in all_code:
                errors.append('Missing QuantConnect imports (use "from AlgorithmImports import *")')

        # Check for undefined symbols that are common mistakes
        common_mistakes = [
            (r'\bself\.Debug\b', r'\bdef Initialize\b', 'Debug called before Initialize'),
            (r'\bself\.Securities\[', r'\bself\.AddEquity\b|\bself\.AddCrypto\b|\bself\.SetUniverseSelection\b',
             'Securities accessed without adding assets'),
        ]

        import re
        for usage_pattern, definition_pattern, error_msg in common_mistakes:
            if re.search(usage_pattern, all_code) and not re.search(definition_pattern, all_code):
                errors.append(error_msg)

        return errors

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
        """Run backtest using QuantConnect MCP client."""
        if self.demo_mode:
            # Return mock results with some variance
            import random
            sharpe = random.uniform(0.2, 1.5)
            return {
                'sharpe_ratio': sharpe,
                'max_drawdown': random.uniform(-0.4, -0.1),
                'total_return': random.uniform(-0.2, 0.8)
            }

        if self.mcp_client is None:
            console.print("[yellow]⚠ MCP client not available - skipping backtest[/yellow]")
            # Return neutral results when backtesting is unavailable
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'skipped': True,
                'reason': 'MCP client not configured'
            }

        try:
            main_code = strategy.get('code', '') or strategy.get('code_files', {}).get('Main.py', '')
            code_files = strategy.get('code_files', {})
            additional_files = {k: v for k, v in code_files.items() if k != 'Main.py'}

            # Run backtest via MCP
            result = await self.mcp_client.backtest(
                code=main_code,
                start_date="2020-01-01",
                end_date="2023-12-31",
                files=additional_files,
                name=strategy.get('name', 'QuantCoder_Strategy')
            )

            if not result.get('success'):
                console.print(f"[red]✗ Backtest failed: {result.get('error', 'Unknown error')}[/red]")
                return {
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'total_return': 0.0,
                    'error': result.get('error')
                }

            # Extract statistics from result
            stats = result.get('statistics', {})
            runtime_stats = result.get('runtime_statistics', {})

            sharpe = self._parse_stat(result.get('sharpe') or stats.get('Sharpe Ratio', 0))
            total_return = self._parse_stat(result.get('total_return') or stats.get('Total Net Profit', 0))
            max_drawdown = self._parse_stat(stats.get('Drawdown', 0))

            return {
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'total_return': total_return,
                'backtest_id': result.get('backtest_id'),
                'full_statistics': stats,
                'runtime_statistics': runtime_stats
            }

        except Exception as e:
            console.print(f"[red]✗ Backtest error: {e}[/red]")
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'error': str(e)
            }

    def _parse_stat(self, value: Any) -> float:
        """Parse a statistic value to float."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Handle percentage strings like "12.5%"
            value = value.strip().rstrip('%')
            try:
                return float(value) / 100 if '%' in str(value) else float(value)
            except ValueError:
                return 0.0
        return 0.0

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

            # Write all code files
            code_files = strategy.get('code_files', {})
            main_code = strategy.get('code', '')

            # Write Main.py
            if main_code or 'Main.py' in code_files:
                main_content = main_code or code_files.get('Main.py', '')
                if main_content:
                    main_path = strategy_dir / 'Main.py'
                    main_path.write_text(main_content, encoding='utf-8')
                    console.print(f"[green]✓ Written: {main_path}[/green]")

            # Write additional component files
            for filename, content in code_files.items():
                if filename != 'Main.py' and content:
                    file_path = strategy_dir / filename
                    file_path.write_text(content, encoding='utf-8')
                    console.print(f"[green]✓ Written: {file_path}[/green]")

            # Write metadata file
            metadata = {
                'name': strategy['name'],
                'paper_title': paper.get('title', ''),
                'paper_url': paper.get('url', ''),
                'paper_authors': paper.get('authors', []),
                'generated_at': datetime.now().isoformat(),
                'backtest_results': {
                    'sharpe_ratio': backtest_result.get('sharpe_ratio'),
                    'max_drawdown': backtest_result.get('max_drawdown'),
                    'total_return': backtest_result.get('total_return')
                },
                'success': success
            }
            metadata_path = strategy_dir / 'metadata.json'
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            console.print(f"[green]✓ Written: {metadata_path}[/green]")

            # Write README for the strategy
            readme_content = f"""# {strategy['name']}

## Source
- **Paper**: {paper.get('title', 'Unknown')}
- **URL**: {paper.get('url', 'N/A')}
- **Authors**: {', '.join(paper.get('authors', ['Unknown']))}

## Backtest Results
- **Sharpe Ratio**: {backtest_result.get('sharpe_ratio', 'N/A'):.2f}
- **Max Drawdown**: {backtest_result.get('max_drawdown', 'N/A'):.2%}
- **Total Return**: {backtest_result.get('total_return', 'N/A'):.2%}

## Generated
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files
"""
            for filename in code_files.keys():
                readme_content += f"- `{filename}`\n"
            if main_code and 'Main.py' not in code_files:
                readme_content += "- `Main.py`\n"

            readme_path = strategy_dir / 'README.md'
            readme_path.write_text(readme_content, encoding='utf-8')
            console.print(f"[green]✓ Written: {readme_path}[/green]")

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
