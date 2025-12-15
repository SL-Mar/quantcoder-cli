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
    Generate QuantConnect code from an article.

    Example: quantcoder generate 1
    """
    config = ctx.obj['config']
    tool = GenerateCodeTool(config)

    with console.status(f"Generating code for article {article_id}..."):
        result = tool.execute(article_id=article_id, max_refine_attempts=max_attempts)

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


if __name__ == '__main__':
    main()
