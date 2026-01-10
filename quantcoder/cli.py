"""Main CLI interface for QuantCoder - inspired by Mistral Vibe CLI."""

import click
import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.markdown import Markdown

from .config import Config
from .chat import InteractiveChat
from .tools import (
    SearchArticlesTool,
    DownloadArticleTool,
    SummarizeArticleTool,
    GenerateCodeTool,
    ValidateCodeTool,
)

console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging with rich handler."""
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True, console=console),
            logging.FileHandler("quantcoder.log")
        ]
    )


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', type=click.Path(), help='Path to config file')
@click.option('--prompt', '-p', type=str, help='Run in non-interactive mode with prompt')
@click.pass_context
def main(ctx, verbose, config, prompt):
    """
    QuantCoder - AI-powered CLI for generating QuantConnect algorithms.

    A conversational interface to transform research articles into trading algorithms.
    """
    setup_logging(verbose)

    # Load configuration
    config_path = Path(config) if config else None
    cfg = Config.load(config_path)

    # Ensure API key is loaded
    try:
        if not cfg.api_key:
            api_key = cfg.load_api_key()
            if not api_key:
                # Prompt for API key on first run
                console.print(
                    "[yellow]No API key found. Please enter your OpenAI API key:[/yellow]"
                )
                api_key = click.prompt("OpenAI API Key", hide_input=True)
                cfg.save_api_key(api_key)
    except EnvironmentError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Please set your OPENAI_API_KEY in the environment or "
            f"create {cfg.home_dir / '.env'}[/yellow]"
        )
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj['config'] = cfg
    ctx.obj['verbose'] = verbose

    # If prompt is provided, run in non-interactive mode
    if prompt:
        from .chat import ProgrammaticChat
        chat = ProgrammaticChat(cfg)
        result = chat.process(prompt)
        console.print(result)
        return

    # If no subcommand, launch interactive mode
    if ctx.invoked_subcommand is None:
        interactive(cfg)


def interactive(config: Config):
    """Launch interactive chat mode."""
    console.print(
        Panel.fit(
            "[bold cyan]QuantCoder v2.0[/bold cyan]\n"
            "AI-powered CLI for QuantConnect algorithms\n\n"
            "[dim]Type 'help' for commands, 'exit' to quit[/dim]",
            title="Welcome",
            border_style="cyan"
        )
    )

    chat = InteractiveChat(config)
    chat.run()


@main.command()
@click.argument('query')
@click.option('--num', default=5, help='Number of results to return')
@click.pass_context
def search(ctx, query, num):
    """
    Search for academic articles on CrossRef.

    Example: quantcoder search "algorithmic trading" --num 3
    """
    config = ctx.obj['config']
    tool = SearchArticlesTool(config)

    with console.status(f"Searching for '{query}'..."):
        result = tool.execute(query=query, max_results=num)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")

        for idx, article in enumerate(result.data, 1):
            published = f" ({article['published']})" if article.get('published') else ""
            console.print(
                f"  [cyan]{idx}.[/cyan] {article['title']}\n"
                f"      [dim]{article['authors']}{published}[/dim]"
            )
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command()
@click.argument('article_id', type=int)
@click.pass_context
def download(ctx, article_id):
    """
    Download an article PDF by ID.

    Example: quantcoder download 1
    """
    config = ctx.obj['config']
    tool = DownloadArticleTool(config)

    with console.status(f"Downloading article {article_id}..."):
        result = tool.execute(article_id=article_id)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command()
@click.argument('article_id', type=int)
@click.pass_context
def summarize(ctx, article_id):
    """
    Summarize a downloaded article.

    Example: quantcoder summarize 1
    """
    config = ctx.obj['config']
    tool = SummarizeArticleTool(config)

    with console.status(f"Analyzing article {article_id}..."):
        result = tool.execute(article_id=article_id)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}\n")
        console.print(Panel(
            Markdown(result.data['summary']),
            title="Summary",
            border_style="green"
        ))
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command(name='generate')
@click.argument('article_id', type=int)
@click.option('--max-attempts', default=6, help='Maximum refinement attempts')
@click.pass_context
def generate_code(ctx, article_id, max_attempts):
    """
    Generate QuantConnect code from an article using BaselinePipeline.

    The pipeline runs:
      1. NLP extraction from PDF
      2. Multi-agent code generation (CoordinatorAgent)
      3. Self-improvement loop with error fixing
      4. MCP backtest validation

    Example: quantcoder generate 1
    """
    config = ctx.obj['config']
    tool = GenerateCodeTool(config)

    console.print(f"[cyan]Starting BaselinePipeline for article {article_id}...[/cyan]")
    console.print("[dim]Pipeline: NLP → CoordinatorAgent → Self-Improvement → Backtest[/dim]\n")

    with console.status(f"Generating code for article {article_id}..."):
        result = tool.execute(article_id=article_id, max_refine_attempts=max_attempts)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}\n")

        # Display strategy info with backtest metrics
        data = result.data
        strategy_name = data.get('strategy_name', 'Unknown')
        paper_title = data.get('paper_title', 'Unknown')
        sharpe = data.get('sharpe_ratio', 0)
        max_dd = data.get('max_drawdown', 0)
        errors_fixed = data.get('errors_fixed', 0)
        code_files = data.get('code_files', {})

        # Strategy summary panel
        summary_text = f"""**Strategy:** {strategy_name}
**Source Paper:** {paper_title}

**Backtest Results:**
- Sharpe Ratio: {sharpe:.2f}
- Max Drawdown: {max_dd:.1%}
- Errors Fixed: {errors_fixed}

**Generated Files:** {', '.join(code_files.keys())}
**Output Path:** {data.get('path', 'N/A')}"""

        console.print(Panel(
            Markdown(summary_text),
            title="[bold]Strategy Summary[/bold]",
            border_style="blue"
        ))

        # Display main code
        from rich.syntax import Syntax
        code = data.get('code', '')
        if code:
            code_display = Syntax(
                code,
                "python",
                theme="monokai",
                line_numbers=True
            )
            console.print("\n")
            console.print(Panel(
                code_display,
                title="Main.py",
                border_style="green"
            ))

        # Show other files summary
        if len(code_files) > 1:
            console.print("\n[dim]Additional files generated:[/dim]")
            for filename in code_files.keys():
                if filename != "Main.py":
                    console.print(f"  • {filename}")
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command()
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    config = ctx.obj['config']

    config_text = f"""
**Model Configuration:**
- Provider: {config.model.provider}
- Model: {config.model.model}
- Temperature: {config.model.temperature}
- Max Tokens: {config.model.max_tokens}

**UI Configuration:**
- Theme: {config.ui.theme}
- Auto Approve: {config.ui.auto_approve}
- Show Token Usage: {config.ui.show_token_usage}

**Tools Configuration:**
- Downloads Directory: {config.tools.downloads_dir}
- Generated Code Directory: {config.tools.generated_code_dir}
- Enabled Tools: {', '.join(config.tools.enabled_tools)}

**Paths:**
- Home Directory: {config.home_dir}
- Config File: {config.home_dir / 'config.toml'}
"""

    console.print(Panel(
        Markdown(config_text),
        title="Configuration",
        border_style="cyan"
    ))


@main.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"QuantCoder v{__version__}")


# ============================================================================
# AUTONOMOUS MODE COMMANDS
# ============================================================================

@main.group()
def auto():
    """
    Autonomous library generation mode.

    Generates a library of N strategies by looping the baseline pipeline
    with quant-perspective prompt variation. Each iteration:

      1. Runs BaselinePipeline (NLP → CoordinatorAgent → backtest)
      2. Analyzes results with QuantPerspectiveRefiner
      3. Varies prompts based on performance (indicators, asset classes, etc.)

    Example:
        quantcoder auto start --query "momentum trading" --count 10
    """
    pass


@auto.command(name='start')
@click.option('--query', required=True, help='Strategy query (e.g., "momentum trading")')
@click.option('--count', default=10, help='Number of strategies to generate (default: 10)')
@click.option('--min-sharpe', default=0.5, type=float, help='Minimum Sharpe ratio threshold')
@click.option('--output', type=click.Path(), help='Output directory for strategy library')
@click.option('--demo', is_flag=True, help='Run in demo mode (no real API calls)')
@click.pass_context
def auto_start(ctx, query, count, min_sharpe, output, demo):
    """
    Start autonomous library generation.

    Generates a library of N strategies by:
      1. Running BaselinePipeline for each strategy
      2. Analyzing results with QuantPerspectiveRefiner
      3. Varying prompts based on quant analysis
      4. Expanding research across indicators, asset classes, timeframes

    Example:
        quantcoder auto start --query "momentum trading" --count 10
        quantcoder auto start --query "mean reversion" --count 5 --min-sharpe 0.8
    """
    import asyncio
    from pathlib import Path
    from quantcoder.pipeline import AutoMode

    config = ctx.obj['config']

    if demo:
        console.print("[yellow]Running in DEMO mode (no real API calls)[/yellow]\n")

    output_dir = Path(output) if output else None

    auto_mode = AutoMode(
        config=config,
        demo_mode=demo
    )

    try:
        asyncio.run(auto_mode.run(
            query=query,
            count=count,
            min_sharpe=min_sharpe,
            output_dir=output_dir
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Auto mode stopped by user[/yellow]")


@auto.command(name='status')
def auto_status():
    """
    Show autonomous mode status and learning statistics.
    """
    from quantcoder.autonomous.database import LearningDatabase

    db = LearningDatabase()

    # Show library stats
    stats = db.get_library_stats()

    console.print("\n[bold cyan]Autonomous Mode Statistics[/bold cyan]\n")
    console.print(f"Total strategies generated: {stats.get('total_strategies', 0)}")
    console.print(f"Successful: {stats.get('successful', 0)}")
    console.print(f"Average Sharpe: {stats.get('avg_sharpe', 0):.2f}\n")

    # Show common errors
    console.print("[bold cyan]Common Errors:[/bold cyan]")
    from quantcoder.autonomous.learner import ErrorLearner
    learner = ErrorLearner(db)
    errors = learner.get_common_errors(limit=5)

    for i, error in enumerate(errors, 1):
        fix_rate = (error['fixed_count'] / error['count'] * 100) if error['count'] > 0 else 0
        console.print(f"  {i}. {error['error_type']}: {error['count']} ({fix_rate:.0f}% fixed)")

    db.close()


@auto.command(name='report')
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
def auto_report(format):
    """
    Generate learning report from autonomous mode.
    """
    from quantcoder.autonomous.database import LearningDatabase

    db = LearningDatabase()
    stats = db.get_library_stats()

    if format == 'json':
        import json
        console.print(json.dumps(stats, indent=2))
    else:
        # Text format
        console.print("\n[bold cyan]Autonomous Mode Learning Report[/bold cyan]\n")
        console.print("=" * 60)

        # Overall stats
        console.print(f"\nTotal Strategies: {stats.get('total_strategies', 0)}")
        console.print(f"Successful: {stats.get('successful', 0)}")
        console.print(f"Average Sharpe: {stats.get('avg_sharpe', 0):.2f}")
        console.print(f"Average Errors: {stats.get('avg_errors', 0):.1f}")
        console.print(f"Average Refinements: {stats.get('avg_refinements', 0):.1f}")

        # Category breakdown
        if stats.get('categories'):
            console.print("\n[bold]Category Breakdown:[/bold]")
            for cat in stats['categories']:
                console.print(f"  • {cat['category']}: {cat['count']} strategies (avg Sharpe: {cat['avg_sharpe']:.2f})")

    db.close()


# ============================================================================
# LIBRARY BUILDER MODE COMMANDS (DEPRECATED - Use 'auto start' instead)
# ============================================================================

@main.group()
def library():
    """
    [DEPRECATED] Library builder mode - Use 'quantcoder auto start' instead.

    The library command is deprecated. Use the new auto mode which provides:
    - BaselinePipeline with self-improvement loop
    - QuantPerspectiveRefiner for quant-driven prompt variation
    - Better backtest integration

    Example:
        quantcoder auto start --query "momentum trading" --count 10
    """
    console.print("[yellow]⚠ DEPRECATED: 'library' commands are deprecated.[/yellow]")
    console.print("[yellow]  Use 'quantcoder auto start --query <query> --count N' instead.[/yellow]\n")


@library.command(name='build')
@click.option('--comprehensive', is_flag=True, help='Build all categories')
@click.option('--max-hours', default=24, type=int, help='Maximum build time in hours')
@click.option('--output', type=click.Path(), help='Output directory for library')
@click.option('--min-sharpe', default=0.5, type=float, help='Minimum Sharpe ratio threshold')
@click.option('--categories', help='Comma-separated list of categories to build')
@click.option('--demo', is_flag=True, help='Run in demo mode (no real API calls)')
@click.pass_context
def library_build(ctx, comprehensive, max_hours, output, min_sharpe, categories, demo):
    """
    Build strategy library from scratch.

    Example:
        quantcoder library build --comprehensive --max-hours 24
        quantcoder library build --categories momentum,mean_reversion
    """
    import asyncio
    from pathlib import Path
    from quantcoder.library import LibraryBuilder

    config = ctx.obj['config']

    if demo:
        console.print("[yellow]Running in DEMO mode (no real API calls)[/yellow]\n")

    output_dir = Path(output) if output else None
    category_list = categories.split(',') if categories else None

    builder = LibraryBuilder(
        config=config,
        demo_mode=demo
    )

    try:
        asyncio.run(builder.build(
            comprehensive=comprehensive,
            max_hours=max_hours,
            output_dir=output_dir,
            min_sharpe=min_sharpe,
            categories=category_list
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Library build stopped by user[/yellow]")


@library.command(name='status')
def library_status():
    """
    Show library build progress.
    """
    import asyncio
    from quantcoder.library import LibraryBuilder

    builder = LibraryBuilder()

    try:
        asyncio.run(builder.status())
    except FileNotFoundError:
        console.print("[yellow]No library build in progress[/yellow]")


@library.command(name='resume')
@click.pass_context
def library_resume(ctx):
    """
    Resume interrupted library build from checkpoint.
    """
    import asyncio
    from quantcoder.library import LibraryBuilder

    config = ctx.obj['config']
    builder = LibraryBuilder(config=config)

    try:
        asyncio.run(builder.resume())
    except KeyboardInterrupt:
        console.print("\n[yellow]Library build stopped by user[/yellow]")


@library.command(name='export')
@click.option('--format', type=click.Choice(['json', 'zip']), default='zip', help='Export format')
@click.option('--output', type=click.Path(), help='Output file path')
def library_export(format, output):
    """
    Export completed library.

    Example:
        quantcoder library export --format zip --output library.zip
        quantcoder library export --format json --output library.json
    """
    import asyncio
    from pathlib import Path
    from quantcoder.library import LibraryBuilder

    output_path = Path(output) if output else None
    builder = LibraryBuilder()

    try:
        asyncio.run(builder.export(format=format, output_file=output_path))
    except Exception as e:
        console.print(f"[red]Error exporting library: {e}[/red]")


# ============================================================================
# EVOLUTION MODE COMMANDS (AlphaEvolve-inspired)
# ============================================================================

EVOLUTIONS_DIR = "data/evolutions"
GENERATED_CODE_DIR = "generated_code"


@main.group()
def evolve():
    """
    AlphaEvolve-inspired strategy evolution.

    Evolve trading algorithms through LLM-generated variations,
    evaluated via QuantConnect backtests.
    """
    pass


@evolve.command(name='start')
@click.argument('article_id', type=int, required=False)
@click.option('--code', type=click.Path(exists=True), help='Path to algorithm file to evolve')
@click.option('--library', 'library_path', type=click.Path(exists=True), help='Path to strategy library directory')
@click.option('--resume', 'resume_id', help='Resume a previous evolution by ID')
@click.option('--gens', 'max_generations', default=10, help='Maximum generations to run')
@click.option('--variants', 'variants_per_gen', default=5, help='Variants per generation')
@click.option('--elite', 'elite_size', default=3, help='Elite pool size')
@click.option('--patience', default=3, help='Stop after N generations without improvement')
@click.option('--qc-user', envvar='QC_USER_ID', help='QuantConnect user ID')
@click.option('--qc-token', envvar='QC_API_TOKEN', help='QuantConnect API token')
@click.option('--qc-project', envvar='QC_PROJECT_ID', type=int, help='QuantConnect project ID')
@click.pass_context
def evolve_start(ctx, article_id, code, library_path, resume_id, max_generations, variants_per_gen,
                 elite_size, patience, qc_user, qc_token, qc_project):
    """
    Evolve trading algorithms using AlphaEvolve-inspired genetic optimization.

    This command takes a generated algorithm (or entire library) and evolves it
    through multiple generations of LLM-generated variations, evaluated via
    QuantConnect backtests.

    ARTICLE_ID: The article number to evolve (must have generated code first)

    Unlike traditional parameter optimization, this explores STRUCTURAL variations:
    - Indicator changes (SMA -> EMA, add RSI, etc.)
    - Risk management modifications
    - Entry/exit logic changes
    - Universe selection tweaks

    Input sources (mutually exclusive):
      ARTICLE_ID  - Evolve strategy generated from article
      --code      - Evolve from single algorithm file
      --library   - Evolve all strategies in a library directory

    Examples:
        quantcoder evolve start 1                    # Evolve article 1's algorithm
        quantcoder evolve start 1 --gens 5          # Run for 5 generations
        quantcoder evolve start --code algo.py      # Evolve from file
        quantcoder evolve start --library ./strategies  # Evolve entire library
        quantcoder evolve start --resume abc123     # Resume evolution abc123
    """
    import asyncio
    import os
    import json
    from pathlib import Path
    from quantcoder.evolver import EvolutionEngine, EvolutionConfig

    # Validate QuantConnect credentials
    if not all([qc_user, qc_token, qc_project]):
        console.print("[red]Error: QuantConnect credentials required.[/red]")
        console.print("")
        console.print("[yellow]Set via environment variables:[/yellow]")
        console.print("  export QC_USER_ID=your_user_id")
        console.print("  export QC_API_TOKEN=your_api_token")
        console.print("  export QC_PROJECT_ID=your_project_id")
        console.print("")
        console.print("[yellow]Or use command options:[/yellow]")
        console.print("  quantcoder evolve start 1 --qc-user ID --qc-token TOKEN --qc-project PROJECT")
        ctx.exit(1)

    # Collect strategies to evolve (list of (code, source_name) tuples)
    strategies_to_evolve = []

    # Handle resume mode
    if resume_id:
        console.print(f"[cyan]Resuming evolution: {resume_id}[/cyan]")
        strategies_to_evolve = [(None, None)]  # Special case for resume
    elif library_path:
        # Load all strategies from library directory
        lib_dir = Path(library_path)
        console.print(f"[cyan]Loading strategies from library: {lib_dir}[/cyan]")

        # Find strategy directories (each should have Main.py)
        strategy_dirs = []
        for item in lib_dir.iterdir():
            if item.is_dir():
                main_py = item / "Main.py"
                if main_py.exists():
                    strategy_dirs.append(item)

        if not strategy_dirs:
            # Check for single .py files in the directory
            py_files = list(lib_dir.glob("*.py"))
            if py_files:
                for py_file in py_files:
                    with open(py_file, 'r') as f:
                        code = f.read()
                    strategies_to_evolve.append((code, py_file.stem))
            else:
                console.print(f"[red]Error: No strategies found in {lib_dir}[/red]")
                console.print("[yellow]Library should contain strategy directories with Main.py[/yellow]")
                ctx.exit(1)
        else:
            for strategy_dir in sorted(strategy_dirs):
                main_py = strategy_dir / "Main.py"
                with open(main_py, 'r') as f:
                    code = f.read()

                # Try to load metadata for source info
                metadata_file = strategy_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    source_name = metadata.get('paper_title', strategy_dir.name)
                else:
                    source_name = strategy_dir.name

                strategies_to_evolve.append((code, source_name))

        console.print(f"[green]Found {len(strategies_to_evolve)} strategies to evolve[/green]\n")
    elif code:
        # Load from file
        code_path = Path(code)
        with open(code_path, 'r') as f:
            baseline_code = f.read()
        strategies_to_evolve = [(baseline_code, str(code_path))]
    elif article_id:
        # Load the generated code for this article
        code_path = Path(GENERATED_CODE_DIR) / f"algorithm_{article_id}.py"
        if not code_path.exists():
            console.print(f"[red]Error: No generated code found for article {article_id}.[/red]")
            console.print(f"[yellow]Run 'quantcoder generate {article_id}' first.[/yellow]")
            ctx.exit(1)

        with open(code_path, 'r') as f:
            baseline_code = f.read()

        # Get article info for reference
        source_paper = f"article_{article_id}"
        articles_file = Path("articles.json")
        if articles_file.exists():
            with open(articles_file, 'r') as f:
                articles = json.load(f)
            if 0 < article_id <= len(articles):
                source_paper = articles[article_id - 1].get('title', source_paper)

        strategies_to_evolve = [(baseline_code, source_paper)]
    else:
        console.print("[red]Error: Provide ARTICLE_ID, --code, --library, or --resume[/red]")
        ctx.exit(1)

    # Create evolution config
    evo_config = EvolutionConfig(
        qc_user_id=qc_user,
        qc_api_token=qc_token,
        qc_project_id=qc_project,
        max_generations=max_generations,
        variants_per_generation=variants_per_gen,
        elite_pool_size=elite_size,
        convergence_patience=patience
    )

    # Display configuration
    console.print("")
    console.print(Panel.fit(
        f"[bold]Strategies to evolve:[/bold] {len(strategies_to_evolve)}\n"
        f"[bold]Max generations:[/bold] {max_generations}\n"
        f"[bold]Variants/gen:[/bold] {variants_per_gen}\n"
        f"[bold]Elite pool size:[/bold] {elite_size}\n"
        f"[bold]Convergence patience:[/bold] {patience}",
        title="[bold cyan]AlphaEvolve Strategy Optimization[/bold cyan]",
        border_style="cyan"
    ))
    console.print("")

    async def run_single_evolution(baseline_code, source_paper, resume=None):
        """Run evolution for a single strategy."""
        engine = EvolutionEngine(evo_config)

        # Set up progress callback
        def on_generation_complete(state, gen):
            best = state.elite_pool.get_best()
            if best and best.fitness:
                console.print(f"  [green]Generation {gen} complete.[/green] Best fitness: {best.fitness:.4f}")

        engine.on_generation_complete = on_generation_complete

        # Run evolution
        if resume:
            result = await engine.evolve(baseline_code="", source_paper="", resume_id=resume)
        else:
            result = await engine.evolve(baseline_code, source_paper)

        return result, engine

    async def run_all_evolutions():
        """Run evolution for all strategies in the list."""
        results = []

        for i, (strategy_code, source_name) in enumerate(strategies_to_evolve, 1):
            if strategy_code is None and source_name is None:
                # Resume mode
                console.print(f"[cyan]Resuming evolution {resume_id}...[/cyan]")
                result, engine = await run_single_evolution(None, None, resume=resume_id)
                results.append((result, engine, "resumed"))
            else:
                console.print(f"\n[cyan]({i}/{len(strategies_to_evolve)}) Evolving: {source_name}[/cyan]")
                result, engine = await run_single_evolution(strategy_code, source_name)
                results.append((result, engine, source_name))

        return results

    try:
        all_results = asyncio.run(run_all_evolutions())

        # Report results for all evolved strategies
        console.print("\n" + "=" * 60)
        console.print("[bold green]EVOLUTION COMPLETE[/bold green]")
        console.print("=" * 60)

        for result, engine, source_name in all_results:
            console.print(f"\n[bold]{source_name}:[/bold]")
            console.print(Panel.fit(
                result.get_summary(),
                title=f"Results",
                border_style="green"
            ))

            # Export best variant
            best = engine.get_best_variant()
            if best:
                # Create output filename based on source
                safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in source_name[:30])
                output_path = Path(GENERATED_CODE_DIR) / f"evolved_{safe_name}_{result.evolution_id}.py"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                engine.export_best_code(str(output_path))
                console.print(f"[green]Best algorithm saved to:[/green] {output_path}")

            console.print(f"[cyan]Evolution ID:[/cyan] {result.evolution_id}")
            console.print(f"[dim]To resume: quantcoder evolve start --resume {result.evolution_id}[/dim]")

        # Summary for library mode
        if len(all_results) > 1:
            console.print("\n[bold cyan]Library Evolution Summary:[/bold cyan]")
            console.print(f"  Total strategies evolved: {len(all_results)}")
            best_fitness = max(
                (r[1].get_best_variant().fitness for r in all_results if r[1].get_best_variant()),
                default=0
            )
            console.print(f"  Best overall fitness: {best_fitness:.4f}" if best_fitness else "")

    except Exception as e:
        console.print(f"[red]Error: Evolution failed - {e}[/red]")
        ctx.exit(1)


@evolve.command(name='list')
def evolve_list():
    """
    List all saved evolution runs.

    Shows evolution IDs, status, and best fitness for each saved evolution.
    """
    import os
    import json
    from pathlib import Path

    evolutions_dir = Path(EVOLUTIONS_DIR)

    if not evolutions_dir.exists():
        console.print("[yellow]No evolutions found.[/yellow]")
        return

    evolution_files = list(evolutions_dir.glob("*.json"))

    if not evolution_files:
        console.print("[yellow]No evolutions found.[/yellow]")
        return

    console.print("\n[bold cyan]Saved Evolutions[/bold cyan]")
    console.print("-" * 60)

    for filepath in sorted(evolution_files):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            evo_id = data.get('evolution_id', 'unknown')
            status = data.get('status', 'unknown')
            generation = data.get('current_generation', 0)
            elite = data.get('elite_pool', {}).get('variants', [])
            best_fitness = elite[0].get('fitness', 'N/A') if elite else 'N/A'

            status_color = {
                'completed': 'green',
                'running': 'yellow',
                'failed': 'red'
            }.get(status, 'white')

            console.print(
                f"  [cyan]{evo_id}[/cyan]: "
                f"Gen {generation}, "
                f"Status: [{status_color}]{status}[/{status_color}], "
                f"Best: {best_fitness}"
            )
        except Exception as e:
            console.print(f"  [red]{filepath.name}: Error reading - {e}[/red]")

    console.print("-" * 60)
    console.print("[dim]Resume with: quantcoder evolve start --resume <id>[/dim]")


@evolve.command(name='show')
@click.argument('evolution_id')
def evolve_show(evolution_id):
    """
    Show details of a specific evolution.

    EVOLUTION_ID: The evolution ID to show
    """
    import json
    from pathlib import Path

    filepath = Path(EVOLUTIONS_DIR) / f"{evolution_id}.json"

    if not filepath.exists():
        console.print(f"[red]Evolution {evolution_id} not found.[/red]")
        return

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Summary
    console.print(Panel.fit(
        f"[bold]Evolution ID:[/bold] {data.get('evolution_id')}\n"
        f"[bold]Status:[/bold] {data.get('status')}\n"
        f"[bold]Generation:[/bold] {data.get('current_generation')}\n"
        f"[bold]Total Variants:[/bold] {len(data.get('all_variants', {}))}\n"
        f"[bold]Source:[/bold] {data.get('source_paper', 'N/A')}",
        title=f"[bold cyan]Evolution {evolution_id}[/bold cyan]",
        border_style="cyan"
    ))

    # Elite pool
    elite = data.get('elite_pool', {}).get('variants', [])
    if elite:
        console.print("\n[bold]Elite Pool:[/bold]")
        for i, variant in enumerate(elite, 1):
            metrics = variant.get('metrics', {})
            console.print(
                f"  {i}. [cyan]{variant['id']}[/cyan] (Gen {variant['generation']}): "
                f"Fitness={variant.get('fitness', 'N/A'):.4f if variant.get('fitness') else 'N/A'}"
            )
            if metrics:
                console.print(
                    f"     Sharpe={metrics.get('sharpe_ratio', 0):.2f}, "
                    f"Return={metrics.get('total_return', 0):.1%}, "
                    f"MaxDD={metrics.get('max_drawdown', 0):.1%}"
                )


@evolve.command(name='export')
@click.argument('evolution_id')
@click.option('--output', type=click.Path(), help='Output file path')
def evolve_export(evolution_id, output):
    """
    Export the best algorithm from an evolution.

    EVOLUTION_ID: The evolution ID to export from
    """
    import json
    from pathlib import Path

    filepath = Path(EVOLUTIONS_DIR) / f"{evolution_id}.json"

    if not filepath.exists():
        console.print(f"[red]Evolution {evolution_id} not found.[/red]")
        return

    with open(filepath, 'r') as f:
        data = json.load(f)

    elite = data.get('elite_pool', {}).get('variants', [])
    if not elite:
        console.print("[red]No elite variants found in this evolution.[/red]")
        return

    best = elite[0]
    output_path = Path(output) if output else Path(GENERATED_CODE_DIR) / f"evolved_{evolution_id}.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(f"# Evolution: {evolution_id}\n")
        f.write(f"# Variant: {best['id']} (Generation {best['generation']})\n")
        f.write(f"# Fitness: {best.get('fitness', 'N/A')}\n")
        if best.get('metrics'):
            f.write(f"# Sharpe: {best['metrics'].get('sharpe_ratio', 0):.2f}\n")
            f.write(f"# Max Drawdown: {best['metrics'].get('max_drawdown', 0):.1%}\n")
        f.write(f"# Description: {best.get('mutation_description', 'N/A')}\n")
        f.write("#\n")
        f.write(best.get('code', ''))

    console.print(f"[green]Exported best variant to:[/green] {output_path}")


if __name__ == '__main__':
    main()
