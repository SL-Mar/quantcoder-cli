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
    BacktestTool,
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
@click.argument('article_ids', type=int, nargs=-1, required=True)
@click.pass_context
def download(ctx, article_ids):
    """
    Download article PDF(s) by ID.

    Examples:
        quantcoder download 1
        quantcoder download 1 2 3
    """
    config = ctx.obj['config']
    tool = DownloadArticleTool(config)

    for article_id in article_ids:
        with console.status(f"Downloading article {article_id}..."):
            result = tool.execute(article_id=article_id)

        if result.success:
            console.print(f"[green]✓[/green] Article {article_id}: {result.message}")
        else:
            console.print(f"[red]✗[/red] Article {article_id}: {result.error}")


@main.command()
@click.argument('article_ids', type=int, nargs=-1, required=True)
@click.pass_context
def summarize(ctx, article_ids):
    """
    Summarize downloaded article(s).

    When multiple articles are provided, also creates a consolidated summary
    with a new ID that can be used with 'generate'.

    Examples:
        quantcoder summarize 1
        quantcoder summarize 1 2 3    # Creates individual + consolidated summary
    """
    config = ctx.obj['config']
    tool = SummarizeArticleTool(config)

    article_ids_list = list(article_ids)

    with console.status(f"Analyzing article(s) {article_ids_list}..."):
        result = tool.execute(article_ids=article_ids_list)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}\n")

        # Show individual summaries
        for summary in result.data.get('summaries', []):
            console.print(Panel(
                Markdown(summary.get('summary_text', '')),
                title=f"Summary #{summary.get('article_id')} - {summary.get('title', 'Unknown')[:50]}",
                border_style="green"
            ))

        # Highlight consolidated summary if created
        if result.data.get('consolidated_summary_id'):
            consolidated_id = result.data['consolidated_summary_id']
            console.print(Panel(
                f"[bold]Consolidated summary created: #{consolidated_id}[/bold]\n\n"
                f"Source articles: {article_ids_list}\n\n"
                f"Use [cyan]quantcoder generate {consolidated_id}[/cyan] to generate code from the combined strategy.",
                title="Consolidated Summary",
                border_style="cyan"
            ))
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command(name='summaries')
@click.pass_context
def list_summaries(ctx):
    """
    List all available summaries (individual and consolidated).

    Shows summary IDs that can be used with 'generate' command.
    """
    from quantcoder.core.summary_store import SummaryStore

    config = ctx.obj['config']
    store = SummaryStore(config.home_dir)
    summaries = store.list_summaries()

    if not summaries['individual'] and not summaries['consolidated']:
        console.print("[yellow]No summaries found. Use 'summarize' to create some.[/yellow]")
        return

    from rich.table import Table

    # Individual summaries
    if summaries['individual']:
        table = Table(title="Individual Summaries")
        table.add_column("ID", style="cyan")
        table.add_column("Article", style="white")
        table.add_column("Title", style="green")
        table.add_column("Type", style="yellow")

        for s in summaries['individual']:
            table.add_row(
                str(s['summary_id']),
                str(s['article_id']),
                s['title'][:50] + "..." if len(s['title']) > 50 else s['title'],
                s['strategy_type']
            )

        console.print(table)
        console.print()

    # Consolidated summaries
    if summaries['consolidated']:
        table = Table(title="Consolidated Summaries")
        table.add_column("ID", style="cyan")
        table.add_column("Source Articles", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Created", style="dim")

        for s in summaries['consolidated']:
            table.add_row(
                str(s['summary_id']),
                str(s['source_article_ids']),
                s['strategy_type'],
                s.get('created_at', '')[:10] if s.get('created_at') else ''
            )

        console.print(table)

    console.print("\n[dim]Use 'quantcoder generate <ID>' to generate code from any summary[/dim]")


@main.command(name='generate')
@click.argument('summary_id', type=int)
@click.option('--max-attempts', default=6, help='Maximum refinement attempts')
@click.option('--open-in-editor', is_flag=True, help='Open generated code in editor (default: Zed)')
@click.option('--editor', default=None, help='Editor to use (overrides config, e.g., zed, code, vim)')
@click.pass_context
def generate_code(ctx, summary_id, max_attempts, open_in_editor, editor):
    """
    Generate QuantConnect code from a summary.

    SUMMARY_ID can be:
    - An individual article summary ID
    - A consolidated summary ID (created from multiple articles)

    Examples:
        quantcoder generate 1              # From article 1 summary
        quantcoder generate 6              # From consolidated summary #6
        quantcoder generate 1 --open-in-editor
    """
    config = ctx.obj['config']
    tool = GenerateCodeTool(config)

    with console.status(f"Generating code for summary #{summary_id}..."):
        result = tool.execute(summary_id=summary_id, max_refine_attempts=max_attempts)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}\n")

        # Display summary
        if result.data.get('summary'):
            console.print(Panel(
                Markdown(result.data['summary']),
                title="Strategy Summary",
                border_style="blue"
            ))

        # Display code
        from rich.syntax import Syntax
        code_display = Syntax(
            result.data['code'],
            "python",
            theme="monokai",
            line_numbers=True
        )
        console.print("\n")
        console.print(Panel(
            code_display,
            title="Generated Code",
            border_style="green"
        ))

        # Open in editor if requested
        if open_in_editor:
            from .editor import open_in_editor as launch_editor, get_editor_display_name
            editor_cmd = editor or config.ui.editor
            editor_name = get_editor_display_name(editor_cmd)
            code_path = result.data.get('path')
            if code_path:
                if launch_editor(code_path, editor_cmd):
                    console.print(f"[cyan]Opened in {editor_name}[/cyan]")
                else:
                    console.print(f"[yellow]Could not open in {editor_name}. Is it installed?[/yellow]")
    else:
        console.print(f"[red]✗[/red] {result.error}")


@main.command(name='validate')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--local-only', is_flag=True, help='Only run local syntax check, skip QuantConnect')
@click.pass_context
def validate_code_cmd(ctx, file_path, local_only):
    """
    Validate algorithm code locally and on QuantConnect.

    Example:
        quantcoder validate generated_code/algorithm_1.py
        quantcoder validate my_algo.py --local-only
    """
    config = ctx.obj['config']
    tool = ValidateCodeTool(config)

    # Read the file
    with open(file_path, 'r') as f:
        code = f.read()

    with console.status(f"Validating {file_path}..."):
        result = tool.execute(code=code, use_quantconnect=not local_only)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
        if result.data and result.data.get('warnings'):
            console.print("[yellow]Warnings:[/yellow]")
            for w in result.data['warnings']:
                console.print(f"  • {w}")
    else:
        console.print(f"[red]✗[/red] {result.error}")
        if result.data and result.data.get('errors'):
            console.print("[red]Errors:[/red]")
            for err in result.data['errors'][:10]:
                console.print(f"  • {err}")


@main.command(name='backtest')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--start', default='2020-01-01', help='Backtest start date (YYYY-MM-DD)')
@click.option('--end', default='2024-01-01', help='Backtest end date (YYYY-MM-DD)')
@click.option('--name', help='Name for the backtest')
@click.pass_context
def backtest_cmd(ctx, file_path, start, end, name):
    """
    Run backtest on QuantConnect.

    Requires QUANTCONNECT_API_KEY and QUANTCONNECT_USER_ID in ~/.quantcoder/.env

    Example:
        quantcoder backtest generated_code/algorithm_1.py
        quantcoder backtest my_algo.py --start 2022-01-01 --end 2024-01-01
    """
    config = ctx.obj['config']

    # Check credentials first
    if not config.has_quantconnect_credentials():
        console.print("[red]Error: QuantConnect credentials not configured[/red]")
        console.print(f"[yellow]Please set QUANTCONNECT_API_KEY and QUANTCONNECT_USER_ID in {config.home_dir / '.env'}[/yellow]")
        return

    tool = BacktestTool(config)

    with console.status(f"Running backtest on {file_path} ({start} to {end})..."):
        result = tool.execute(file_path=file_path, start_date=start, end_date=end, name=name)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}\n")

        # Display results table
        from rich.table import Table
        table = Table(title="Backtest Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Backtest ID", str(result.data.get('backtest_id', 'N/A')))
        table.add_row("Sharpe Ratio", f"{result.data.get('sharpe_ratio', 0):.2f}")
        table.add_row("Total Return", str(result.data.get('total_return', 'N/A')))

        # Add statistics
        stats = result.data.get('statistics', {})
        for key, value in list(stats.items())[:8]:
            table.add_row(key, str(value))

        console.print(table)
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
    Autonomous self-improving mode for strategy generation.

    This mode runs continuously, learning from errors and improving over time.
    """
    pass


@auto.command(name='start')
@click.option('--query', required=True, help='Strategy query (e.g., "momentum trading")')
@click.option('--max-iterations', default=50, help='Maximum iterations to run')
@click.option('--min-sharpe', default=0.5, type=float, help='Minimum Sharpe ratio threshold')
@click.option('--output', type=click.Path(), help='Output directory for strategies')
@click.option('--demo', is_flag=True, help='Run in demo mode (no real API calls)')
@click.pass_context
def auto_start(ctx, query, max_iterations, min_sharpe, output, demo):
    """
    Start autonomous strategy generation.

    Example:
        quantcoder auto start --query "momentum trading" --max-iterations 50
    """
    import asyncio
    from pathlib import Path
    from quantcoder.autonomous import AutonomousPipeline

    config = ctx.obj['config']

    if demo:
        console.print("[yellow]Running in DEMO mode (no real API calls)[/yellow]\n")

    output_dir = Path(output) if output else None

    pipeline = AutonomousPipeline(
        config=config,
        demo_mode=demo
    )

    try:
        asyncio.run(pipeline.run(
            query=query,
            max_iterations=max_iterations,
            min_sharpe=min_sharpe,
            output_dir=output_dir
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Autonomous mode stopped by user[/yellow]")


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
# LIBRARY BUILDER MODE COMMANDS
# ============================================================================

@main.group()
def library():
    """
    Library builder mode - Build comprehensive strategy library from scratch.

    This mode systematically generates strategies across all major categories.
    """
    pass


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
@click.option('--resume', 'resume_id', help='Resume a previous evolution by ID')
@click.option('--gens', 'max_generations', default=10, help='Maximum generations to run')
@click.option('--variants', 'variants_per_gen', default=5, help='Variants per generation')
@click.option('--elite', 'elite_size', default=3, help='Elite pool size')
@click.option('--patience', default=3, help='Stop after N generations without improvement')
@click.option('--qc-user', envvar='QC_USER_ID', help='QuantConnect user ID')
@click.option('--qc-token', envvar='QC_API_TOKEN', help='QuantConnect API token')
@click.option('--qc-project', envvar='QC_PROJECT_ID', type=int, help='QuantConnect project ID')
@click.pass_context
def evolve_start(ctx, article_id, code, resume_id, max_generations, variants_per_gen,
                 elite_size, patience, qc_user, qc_token, qc_project):
    """
    Evolve a trading algorithm using AlphaEvolve-inspired optimization.

    This command takes a generated algorithm and evolves it through multiple
    generations of LLM-generated variations, evaluated via QuantConnect backtests.

    ARTICLE_ID: The article number to evolve (must have generated code first)

    Unlike traditional parameter optimization, this explores STRUCTURAL variations:
    - Indicator changes (SMA -> EMA, add RSI, etc.)
    - Risk management modifications
    - Entry/exit logic changes
    - Universe selection tweaks

    Examples:
        quantcoder evolve start 1                    # Evolve article 1's algorithm
        quantcoder evolve start 1 --gens 5          # Run for 5 generations
        quantcoder evolve start --code algo.py      # Evolve from file
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

    # Handle resume mode
    if resume_id:
        console.print(f"[cyan]Resuming evolution: {resume_id}[/cyan]")
        baseline_code = None
        source_paper = None
    elif code:
        # Load from file
        code_path = Path(code)
        with open(code_path, 'r') as f:
            baseline_code = f.read()
        source_paper = str(code_path)
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
    else:
        console.print("[red]Error: Provide ARTICLE_ID, --code, or --resume[/red]")
        ctx.exit(1)

    # Create evolution config
    config = EvolutionConfig(
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
        f"[bold]Max generations:[/bold] {max_generations}\n"
        f"[bold]Variants/gen:[/bold] {variants_per_gen}\n"
        f"[bold]Elite pool size:[/bold] {elite_size}\n"
        f"[bold]Convergence patience:[/bold] {patience}",
        title="[bold cyan]AlphaEvolve Strategy Optimization[/bold cyan]",
        border_style="cyan"
    ))
    console.print("")

    async def run_evolution():
        engine = EvolutionEngine(config)

        # Set up progress callback
        def on_generation_complete(state, gen):
            best = state.elite_pool.get_best()
            if best and best.fitness:
                console.print(f"\n[green]Generation {gen} complete.[/green] Best fitness: {best.fitness:.4f}")

        engine.on_generation_complete = on_generation_complete

        # Run evolution
        if resume_id:
            result = await engine.evolve(baseline_code="", source_paper="", resume_id=resume_id)
        else:
            result = await engine.evolve(baseline_code, source_paper)

        return result, engine

    try:
        result, engine = asyncio.run(run_evolution())

        # Report results
        console.print("")
        console.print(Panel.fit(
            result.get_summary(),
            title="[bold green]EVOLUTION COMPLETE[/bold green]",
            border_style="green"
        ))

        # Export best variant
        best = engine.get_best_variant()
        if best:
            output_path = Path(GENERATED_CODE_DIR) / f"evolved_{result.evolution_id}.py"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            engine.export_best_code(str(output_path))
            console.print(f"\n[green]Best algorithm saved to:[/green] {output_path}")

        console.print(f"\n[cyan]Evolution ID:[/cyan] {result.evolution_id}")
        console.print(f"[dim]To resume: quantcoder evolve start --resume {result.evolution_id}[/dim]")

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


# ============================================================================
# SCHEDULED AUTOMATION COMMANDS
# ============================================================================

@main.group()
def schedule():
    """
    Automated scheduled strategy generation.

    Run the full pipeline on a schedule: discover papers, generate strategies,
    backtest, and publish to Notion.
    """
    pass


@schedule.command(name='start')
@click.option('--interval', type=click.Choice(['hourly', 'daily', 'weekly']), default='daily',
              help='Run frequency')
@click.option('--hour', default=6, type=int, help='Hour to run (for daily/weekly)')
@click.option('--day', default='mon', help='Day of week (for weekly)')
@click.option('--queries', help='Comma-separated search queries')
@click.option('--min-sharpe', default=0.5, type=float, help='Acceptance criteria - min Sharpe to keep algo')
@click.option('--max-strategies', default=10, type=int, help='Batch limit - max strategies per run')
@click.option('--notion-min-sharpe', default=0.5, type=float, help='Min Sharpe for Notion article (defaults to min-sharpe)')
@click.option('--output', type=click.Path(), help='Output directory')
@click.option('--run-now', is_flag=True, help='Run immediately before starting schedule')
@click.pass_context
def schedule_start(ctx, interval, hour, day, queries, min_sharpe, max_strategies,
                   notion_min_sharpe, output, run_now):
    """
    Start the automated scheduled pipeline.

    This runs the full workflow on a schedule:
    1. Search for new research papers
    2. Generate and backtest strategies
    3. Publish successful strategies to Notion
    4. Keep algorithms in QuantConnect

    Examples:
        quantcoder schedule start --interval daily --hour 6
        quantcoder schedule start --interval weekly --day mon --hour 9
        quantcoder schedule start --queries "momentum,mean reversion" --run-now
    """
    import asyncio
    from pathlib import Path
    from quantcoder.scheduler import (
        ScheduledRunner,
        ScheduleConfig,
        ScheduleInterval,
        AutomatedBacktestPipeline,
        PipelineConfig,
    )

    config = ctx.obj['config']

    # Build schedule config
    interval_map = {
        'hourly': ScheduleInterval.HOURLY,
        'daily': ScheduleInterval.DAILY,
        'weekly': ScheduleInterval.WEEKLY,
    }

    schedule_config = ScheduleConfig(
        interval=interval_map[interval],
        hour=hour,
        day_of_week=day,
    )

    # Build pipeline config
    search_queries = queries.split(',') if queries else None
    output_dir = Path(output) if output else None

    pipeline_config = PipelineConfig(
        min_sharpe_ratio=min_sharpe,
        max_strategies_per_run=max_strategies,
        notion_min_sharpe=notion_min_sharpe,
    )

    if search_queries:
        pipeline_config.search_queries = [q.strip() for q in search_queries]
    if output_dir:
        pipeline_config.output_dir = output_dir

    # Create pipeline and runner
    pipeline = AutomatedBacktestPipeline(config=config, pipeline_config=pipeline_config)

    async def run_pipeline():
        result = await pipeline.run()
        return {
            "strategies_generated": result.strategies_generated,
            "strategies_published": result.strategies_published,
        }

    runner = ScheduledRunner(
        pipeline_func=run_pipeline,
        schedule_config=schedule_config,
    )

    try:
        if run_now:
            console.print("[cyan]Running pipeline immediately...[/cyan]")
            asyncio.run(runner.run_once())

        asyncio.run(runner.run_forever())
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped by user[/yellow]")


@schedule.command(name='run')
@click.option('--queries', help='Comma-separated search queries')
@click.option('--min-sharpe', default=0.5, type=float, help='Acceptance criteria - min Sharpe to keep algo')
@click.option('--max-strategies', default=10, type=int, help='Batch limit - max strategies per run')
@click.option('--output', type=click.Path(), help='Output directory')
@click.pass_context
def schedule_run(ctx, queries, min_sharpe, max_strategies, output):
    """
    Run the automated pipeline once (no scheduling).

    Good for testing or manual runs.

    Examples:
        quantcoder schedule run
        quantcoder schedule run --queries "factor investing" --min-sharpe 1.0
    """
    import asyncio
    from pathlib import Path
    from quantcoder.scheduler import AutomatedBacktestPipeline, PipelineConfig

    config = ctx.obj['config']

    # Build pipeline config
    search_queries = queries.split(',') if queries else None
    output_dir = Path(output) if output else None

    pipeline_config = PipelineConfig(
        min_sharpe_ratio=min_sharpe,
        max_strategies_per_run=max_strategies,
    )

    if search_queries:
        pipeline_config.search_queries = [q.strip() for q in search_queries]
    if output_dir:
        pipeline_config.output_dir = output_dir

    pipeline = AutomatedBacktestPipeline(config=config, pipeline_config=pipeline_config)

    try:
        asyncio.run(pipeline.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline stopped by user[/yellow]")


@schedule.command(name='status')
def schedule_status():
    """
    Show scheduler status and run history.
    """
    import json
    from pathlib import Path

    state_file = Path.home() / ".quantcoder" / "scheduler_state.json"

    if not state_file.exists():
        console.print("[yellow]No scheduler runs recorded yet.[/yellow]")
        console.print("[dim]Run 'quantcoder schedule start' to begin.[/dim]")
        return

    with open(state_file, 'r') as f:
        state = json.load(f)

    from rich.table import Table

    table = Table(title="Scheduler Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Runs", str(state.get('total_runs', 0)))
    table.add_row("Successful Runs", str(state.get('successful_runs', 0)))
    table.add_row("Failed Runs", str(state.get('failed_runs', 0)))
    table.add_row("Strategies Generated", str(state.get('strategies_generated', 0)))
    table.add_row("Strategies Published", str(state.get('strategies_published', 0)))
    table.add_row("Last Run", state.get('last_run_time', 'Never'))
    table.add_row("Last Run Success", 'Yes' if state.get('last_run_success', True) else 'No')

    console.print(table)


@schedule.command(name='config')
@click.option('--notion-key', help='Set Notion API key')
@click.option('--notion-db', help='Set Notion database ID')
@click.option('--show', is_flag=True, help='Show current configuration')
def schedule_config(notion_key, notion_db, show):
    """
    Configure scheduler settings (Notion integration, etc.)

    Examples:
        quantcoder schedule config --show
        quantcoder schedule config --notion-key secret_xxx --notion-db abc123
    """
    import os
    from pathlib import Path

    env_file = Path.home() / ".quantcoder" / ".env"

    if show:
        console.print("\n[bold cyan]Scheduler Configuration[/bold cyan]\n")

        # Check Notion settings
        notion_key_set = bool(os.getenv('NOTION_API_KEY'))
        notion_db_set = bool(os.getenv('NOTION_DATABASE_ID'))

        console.print(f"NOTION_API_KEY: {'[green]Set[/green]' if notion_key_set else '[yellow]Not set[/yellow]'}")
        console.print(f"NOTION_DATABASE_ID: {'[green]Set[/green]' if notion_db_set else '[yellow]Not set[/yellow]'}")

        console.print(f"\n[dim]Environment file: {env_file}[/dim]")
        return

    if not notion_key and not notion_db:
        console.print("[yellow]No configuration options provided. Use --show to see current config.[/yellow]")
        return

    # Load existing env file
    env_vars = {}
    if env_file.exists():
        from dotenv import dotenv_values
        env_vars = dict(dotenv_values(env_file))

    # Update values
    if notion_key:
        env_vars['NOTION_API_KEY'] = notion_key
        console.print("[green]Set NOTION_API_KEY[/green]")

    if notion_db:
        env_vars['NOTION_DATABASE_ID'] = notion_db
        console.print("[green]Set NOTION_DATABASE_ID[/green]")

    # Write back
    env_file.parent.mkdir(parents=True, exist_ok=True)
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"\n[dim]Configuration saved to {env_file}[/dim]")


if __name__ == '__main__':
    main()
