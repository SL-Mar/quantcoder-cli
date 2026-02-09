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


def setup_logging(verbose: bool = False, config: Config = None):
    """Configure logging with rich handler and rotation.

    Uses the new centralized logging system with:
    - Log rotation (configurable size and backup count)
    - Structured JSON logging (in addition to console output)
    - Optional webhook alerting for errors
    """
    from quantcoder.logging_config import setup_logging as setup_qc_logging

    # Get logging config if available
    logging_config = None
    if config:
        try:
            logging_config = config.get_logging_config()
        except Exception:
            pass  # Use defaults if config fails

    # Create rich console handler
    rich_handler = RichHandler(
        rich_tracebacks=True,
        console=console,
        show_time=True,
        show_path=False,
    )
    rich_handler._custom_formatter = True  # Signal to not override formatter

    # Setup centralized logging
    setup_qc_logging(
        verbose=verbose,
        config=logging_config,
        console_handler=rich_handler,
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
    # Load configuration first so logging can use it
    config_path = Path(config) if config else None
    cfg = Config.load(config_path)

    # Setup logging with config (enables rotation, JSON logs, webhooks)
    setup_logging(verbose, cfg)

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
    banner = (
        "[bold cyan]"
        "   ____                    _    ____          _\n"
        "  / __ \\  _   _  __ _ _ _| |_ / ___|___   __| | ___ _ __\n"
        " | |  | || | | |/ _` | '_ \\  _| |   / _ \\ / _` |/ _ \\ '__|\n"
        " | |__| || |_| | (_| | | | | || |__| (_) | (_| |  __/ |\n"
        "  \\___\\_\\ \\__,_|\\__,_|_| |_|\\__\\____\\___/ \\__,_|\\___|_|[/bold cyan]\n"
        "\n"
        "  [dim]v2.0  |  AI-powered QuantConnect algorithm pipeline[/dim]\n"
        "  [dim]Type 'help' for commands, 'exit' to quit[/dim]"
    )
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))

    chat = InteractiveChat(config)
    chat.run()


@main.command()
@click.argument('query')
@click.option('--num', default=5, help='Number of results to return')
@click.option('--deep', is_flag=True, help='Use Tavily for semantic deep search (requires TAVILY_API_KEY)')
@click.option('--no-filter', is_flag=True, help='Skip LLM relevance filtering (with --deep)')
@click.pass_context
def search(ctx, query, num, deep, no_filter):
    """
    Search for academic articles.

    By default uses CrossRef API for keyword search.
    With --deep flag, uses Tavily for semantic search + LLM filtering.

    Examples:
        quantcoder search "algorithmic trading" --num 3
        quantcoder search "momentum strategy" --deep
        quantcoder search "mean reversion" --deep --num 10
    """
    config = ctx.obj['config']

    if deep:
        # Use Tavily deep search
        from .tools import DeepSearchTool
        tool = DeepSearchTool(config)

        with console.status(f"Deep searching for '{query}'..."):
            result = tool.execute(
                query=query,
                max_results=num,
                filter_relevance=not no_filter,
            )

        if result.success:
            console.print(f"[green]✓[/green] {result.message}\n")

            for idx, article in enumerate(result.data, 1):
                score = article.get('relevance_score', 0)
                score_color = "green" if score > 0.7 else "yellow" if score > 0.5 else "dim"
                published = f" ({article['published']})" if article.get('published') else ""

                console.print(
                    f"  [cyan]{idx}.[/cyan] {article['title']}\n"
                    f"      [{score_color}]Score: {score:.2f}[/{score_color}]{published}\n"
                    f"      [dim]{article['URL'][:60]}...[/dim]"
                )

            console.print(f"\n[dim]Use 'quantcoder download <ID>' to get articles[/dim]")
        else:
            console.print(f"[red]✗[/red] {result.error}")
    else:
        # Use arXiv search (default, open-access)
        tool = SearchArticlesTool(config)

        with console.status(f"Searching arXiv for '{query}'..."):
            result = tool.execute(query=query, max_results=num)

        if result.success:
            console.print(f"[green]✓[/green] {result.message}")

            for idx, article in enumerate(result.data, 1):
                published = f" ({article['published']})" if article.get('published') else ""
                cats = article.get('categories', [])
                cat_str = f" [magenta][{', '.join(cats[:3])}][/magenta]" if cats else ""
                console.print(
                    f"  [cyan]{idx}.[/cyan] {article['title']}\n"
                    f"      [dim]{article['authors']}{published}[/dim]{cat_str}"
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
            console.print(f"[red]✗[/red] Article {article_id} download failed:")
            for line in result.error.split("\n"):
                console.print(f"  [yellow]{line}[/yellow]")


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


def _publish_to_notion(config, summary_id: int, code: str, sharpe: float,
                       backtest_data: dict, console):
    """Publish strategy article to Notion after successful backtest."""
    import os
    from quantcoder.core.summary_store import SummaryStore

    # Check Notion credentials
    notion_key = os.getenv('NOTION_API_KEY')
    notion_db = os.getenv('NOTION_DATABASE_ID')

    if not notion_key or not notion_db:
        console.print("[yellow]⚠ Notion credentials not configured[/yellow]")
        console.print(f"[dim]Set NOTION_API_KEY and NOTION_DATABASE_ID in {config.home_dir / '.env'}[/dim]")
        console.print("[dim]Use 'quantcoder schedule config' to configure[/dim]")
        return

    try:
        from quantcoder.scheduler import NotionClient, StrategyArticle

        # Get summary data
        store = SummaryStore(config.home_dir)
        summary = store.get_summary(summary_id)

        if not summary:
            console.print(f"[yellow]⚠ Could not retrieve summary {summary_id} for article[/yellow]")
            return

        # Determine title and description based on summary type
        if summary.get('is_consolidated'):
            paper_title = f"Consolidated from articles {summary.get('source_article_ids', [])}"
            description = summary.get('merged_description', '')
            strategy_type = summary.get('merged_strategy_type', 'hybrid')
            paper_url = ""
            authors = []
        else:
            paper_title = summary.get('title', f'Strategy {summary_id}')
            description = summary.get('summary_text', '')
            strategy_type = summary.get('strategy_type', 'unknown')
            paper_url = summary.get('url', '')
            authors = [summary.get('authors', 'Unknown')]

        # Generate article title based on performance
        if sharpe >= 1.5:
            perf_label = "High-Performance"
        elif sharpe >= 1.0:
            perf_label = "Strong"
        elif sharpe >= 0.5:
            perf_label = "Viable"
        else:
            perf_label = "Experimental"

        strategy_type_display = strategy_type.replace("_", " ").title()
        title = f"{perf_label} {strategy_type_display} Strategy"

        # Build backtest results for article
        backtest_results = {
            'sharpe_ratio': sharpe,
            'total_return': backtest_data.get('total_return', 0),
            'max_drawdown': backtest_data.get('statistics', {}).get('Max Drawdown', 0),
            'win_rate': backtest_data.get('statistics', {}).get('Win Rate', 'N/A'),
        }

        # Create StrategyArticle directly
        article = StrategyArticle(
            title=title,
            paper_title=paper_title,
            paper_url=paper_url,
            paper_authors=authors,
            strategy_summary=description,
            strategy_type=strategy_type,
            backtest_results=backtest_results,
            code_snippet=code[:2000] if len(code) > 2000 else code,
            tags=[strategy_type_display]
        )

        # Publish to Notion
        notion_client = NotionClient(api_key=notion_key, database_id=notion_db)
        page = notion_client.create_strategy_page(article)

        if page:
            console.print(f"[green]✓ Published to Notion[/green] (page: {page.id[:8]}...)")
        else:
            console.print("[yellow]⚠ Failed to create Notion page[/yellow]")

    except ImportError as e:
        console.print(f"[yellow]⚠ Scheduler module not available: {e}[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to publish to Notion: {e}[/red]")


def _run_evolution(config, code: str, source_name: str, max_generations: int,
                   variants_per_gen: int, start_date: str, end_date: str, console):
    """Run evolution on a strategy to improve it."""
    import asyncio
    import os

    try:
        from quantcoder.evolver import EvolutionEngine, EvolutionConfig

        # Get QC credentials
        qc_user = os.getenv('QC_USER_ID') or os.getenv('QUANTCONNECT_USER_ID')
        qc_token = os.getenv('QC_API_TOKEN') or os.getenv('QUANTCONNECT_API_KEY')
        qc_project = os.getenv('QC_PROJECT_ID')

        if not all([qc_user, qc_token]):
            console.print("[yellow]⚠ QC credentials not fully configured for evolution[/yellow]")
            return None

        # Create evolution config
        evo_config = EvolutionConfig(
            qc_user_id=qc_user,
            qc_api_token=qc_token,
            qc_project_id=int(qc_project) if qc_project else None,
            max_generations=max_generations,
            variants_per_generation=variants_per_gen,
            backtest_start_date=start_date,
            backtest_end_date=end_date,
        )

        engine = EvolutionEngine(evo_config)

        # Progress callback
        def on_gen_complete(state, gen):
            best = state.elite_pool.get_best()
            if best and best.fitness:
                console.print(f"  [dim]Gen {gen}: Best fitness = {best.fitness:.4f}[/dim]")

        engine.on_generation_complete = on_gen_complete

        async def run_evo():
            return await engine.evolve(code, source_name)

        # Run evolution
        with console.status("Evolving strategy..."):
            result = asyncio.run(run_evo())

        # Get best variant
        best = engine.get_best_variant()
        if best and best.code:
            return {
                'code': best.code,
                'sharpe': best.metrics.get('sharpe_ratio', 0) if best.metrics else 0,
                'backtest_data': best.metrics or {},
                'evolution_id': result.evolution_id,
            }

        return None

    except ImportError as e:
        console.print(f"[yellow]⚠ Evolution module not available: {e}[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]✗ Evolution failed: {e}[/red]")
        return None


@main.command(name='generate')
@click.argument('summary_id', type=int)
@click.option('--max-attempts', default=6, help='Maximum refinement attempts')
@click.option('--open-in-editor', is_flag=True, help='Open generated code in editor (default: Zed)')
@click.option('--editor', default=None, help='Editor to use (overrides config, e.g., zed, code, vim)')
@click.option('--backtest', is_flag=True, help='Run backtest on QuantConnect after generation')
@click.option('--min-sharpe', default=0.5, type=float, help='Min Sharpe to keep algo and publish to Notion (with --backtest)')
@click.option('--start-date', default='2020-01-01', help='Backtest start date (with --backtest)')
@click.option('--end-date', default='2024-01-01', help='Backtest end date (with --backtest)')
@click.option('--evolve', is_flag=True, help='Evolve strategy after backtest passes (with --backtest)')
@click.option('--gens', default=5, type=int, help='Number of evolution generations (with --evolve)')
@click.option('--variants', default=3, type=int, help='Variants per generation (with --evolve)')
@click.pass_context
def generate_code(ctx, summary_id, max_attempts, open_in_editor, editor, backtest, min_sharpe, start_date, end_date, evolve, gens, variants):
    """
    Generate QuantConnect code from a summary.

    SUMMARY_ID can be:
    - An individual article summary ID
    - A consolidated summary ID (created from multiple articles)

    With --backtest flag:
    - Runs backtest on QuantConnect after code generation
    - If Sharpe >= min-sharpe: keeps algo in QC and publishes article to Notion
    - If Sharpe < min-sharpe: reports results but does not publish

    With --evolve flag (requires --backtest):
    - After backtest passes, evolves the strategy for N generations
    - Publishes the best evolved variant to Notion

    Examples:
        quantcoder generate 1              # From article 1 summary
        quantcoder generate 6              # From consolidated summary #6
        quantcoder generate 1 --open-in-editor
        quantcoder generate 1 --backtest   # Generate, backtest, and publish if good
        quantcoder generate 1 --backtest --min-sharpe 1.0
        quantcoder generate 1 --backtest --evolve --gens 5  # Evolve after backtest
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

        # Handle backtest if requested
        if backtest:
            code_path = result.data.get('path')
            if not code_path:
                console.print("[red]✗[/red] Cannot backtest: no code file path")
                return

            # Check QuantConnect credentials
            if not config.has_quantconnect_credentials():
                console.print("[red]Error: QuantConnect credentials not configured[/red]")
                console.print(f"[yellow]Please set QUANTCONNECT_API_KEY and QUANTCONNECT_USER_ID in {config.home_dir / '.env'}[/yellow]")
                return

            console.print("\n")
            backtest_tool = BacktestTool(config)

            with console.status(f"Running backtest ({start_date} to {end_date})..."):
                bt_result = backtest_tool.execute(
                    file_path=code_path,
                    start_date=start_date,
                    end_date=end_date,
                    name=f"Summary_{summary_id}"
                )

            if not bt_result.success:
                console.print(f"[red]✗[/red] Backtest failed: {bt_result.error}")
                return

            try:
                sharpe = float(bt_result.data.get('sharpe_ratio', 0))
            except (TypeError, ValueError):
                sharpe = 0.0
            console.print(f"[green]✓[/green] Backtest complete: Sharpe = {sharpe:.2f}")

            # Display backtest results
            from rich.table import Table
            bt_table = Table(title="Backtest Results")
            bt_table.add_column("Metric", style="cyan")
            bt_table.add_column("Value", style="green")

            bt_table.add_row("Sharpe Ratio", f"{sharpe:.2f}")
            bt_table.add_row("Total Return", str(bt_result.data.get('total_return', 'N/A')))

            cagr = bt_result.data.get('cagr')
            bt_table.add_row("CAGR", f"{cagr:.1%}" if isinstance(cagr, (int, float)) else "N/A")

            max_dd = bt_result.data.get('max_drawdown')
            bt_table.add_row("Max Drawdown", f"{max_dd:.1%}" if isinstance(max_dd, (int, float)) else "N/A")

            win_rate = bt_result.data.get('win_rate')
            bt_table.add_row("Win Rate", f"{win_rate:.1%}" if isinstance(win_rate, (int, float)) else "N/A")

            total_trades = bt_result.data.get('total_trades')
            bt_table.add_row("Total Trades", str(total_trades) if total_trades is not None else "N/A")

            console.print(bt_table)

            # Check acceptance criteria
            if sharpe >= min_sharpe:
                console.print(f"\n[green]✓ Sharpe {sharpe:.2f} >= {min_sharpe} - ACCEPTED[/green]")

                final_code = result.data['code']
                final_sharpe = sharpe
                final_backtest_data = bt_result.data

                # Run evolution if requested
                if evolve:
                    console.print(f"\n[cyan]Evolving strategy for {gens} generations...[/cyan]")
                    evolved_result = _run_evolution(
                        config=config,
                        code=result.data['code'],
                        source_name=f"Summary_{summary_id}",
                        max_generations=gens,
                        variants_per_gen=variants,
                        start_date=start_date,
                        end_date=end_date,
                        console=console
                    )

                    if evolved_result:
                        final_code = evolved_result['code']
                        final_sharpe = evolved_result['sharpe']
                        final_backtest_data = evolved_result['backtest_data']
                        console.print(f"[green]✓ Evolution complete: Sharpe improved to {final_sharpe:.2f}[/green]")

                # Publish to Notion
                console.print("[cyan]Publishing to Notion...[/cyan]")
                _publish_to_notion(
                    config=config,
                    summary_id=summary_id,
                    code=final_code,
                    sharpe=final_sharpe,
                    backtest_data=final_backtest_data,
                    console=console
                )
            else:
                console.print(f"\n[yellow]⚠ Sharpe {sharpe:.2f} < {min_sharpe} - NOT PUBLISHED[/yellow]")
                console.print("[dim]Strategy kept locally but not published to Notion[/dim]")
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
        sharpe = result.data.get('sharpe_ratio')
        try:
            table.add_row("Sharpe Ratio", f"{float(sharpe):.2f}" if sharpe is not None else "N/A")
        except (ValueError, TypeError):
            table.add_row("Sharpe Ratio", str(sharpe))
        table.add_row("Total Return", str(result.data.get('total_return') or 'N/A'))

        cagr = result.data.get('cagr')
        table.add_row("CAGR", f"{cagr:.1%}" if isinstance(cagr, (int, float)) else "N/A")

        max_dd = result.data.get('max_drawdown')
        table.add_row("Max Drawdown", f"{max_dd:.1%}" if isinstance(max_dd, (int, float)) else "N/A")

        win_rate = result.data.get('win_rate')
        table.add_row("Win Rate", f"{win_rate:.1%}" if isinstance(win_rate, (int, float)) else "N/A")

        total_trades = result.data.get('total_trades')
        table.add_row("Total Trades", str(total_trades) if total_trades is not None else "N/A")

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
@click.option('--gens', 'max_generations', default=3, help='Maximum generations to run')
@click.option('--variants', 'variants_per_gen', default=5, help='Variants per generation')
@click.option('--elite', 'elite_size', default=3, help='Elite pool size')
@click.option('--patience', default=3, help='Stop after N generations without improvement')
@click.option('--qc-user', envvar='QC_USER_ID', help='QuantConnect user ID')
@click.option('--qc-token', envvar='QC_API_TOKEN', help='QuantConnect API token')
@click.option('--qc-project', envvar='QC_PROJECT_ID', type=int, help='QuantConnect project ID')
@click.option('--push-to-qc', is_flag=True, help='Push best variant to a new QuantConnect project after evolution')
@click.pass_context
def evolve_start(ctx, article_id, code, resume_id, max_generations, variants_per_gen,
                 elite_size, patience, qc_user, qc_token, qc_project, push_to_qc):
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
        quantcoder evolve start 1 --gens 3          # Run for 3 generations
        quantcoder evolve start --code algo.py      # Evolve from file
        quantcoder evolve start --resume abc123     # Resume evolution abc123
        quantcoder evolve start 1 --push-to-qc     # Push best variant to QuantConnect
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

        # Push best variant to QuantConnect if requested
        if push_to_qc and best:
            try:
                from quantcoder.evolver.evaluator import QCEvaluator
                from quantcoder.evolver.config import EvolutionConfig as EvoConfig

                evo_cfg = EvoConfig(
                    qc_user_id=qc_user,
                    qc_api_token=qc_token,
                    qc_project_id=qc_project,
                )
                evaluator = QCEvaluator(evo_cfg)

                async def push_to_quantconnect():
                    project_name = f"Evolved_{result.evolution_id}"
                    project_id = await evaluator.create_project(project_name)
                    if not project_id:
                        return None, None
                    if not await evaluator.update_project_code(project_id, best.code):
                        return project_id, None
                    compile_id = await evaluator.compile_project(project_id)
                    return project_id, compile_id

                console.print("\n[cyan]Pushing best variant to QuantConnect...[/cyan]")
                proj_id, comp_id = asyncio.run(push_to_quantconnect())

                if proj_id and comp_id:
                    console.print(f"[green]✓ Created QC project:[/green] Evolved_{result.evolution_id}")
                    console.print(f"  Project ID: {proj_id}")
                    console.print(f"  URL: https://www.quantconnect.com/terminal/{proj_id}")
                elif proj_id:
                    console.print(f"[yellow]⚠ Project created (ID: {proj_id}) but compilation failed[/yellow]")
                else:
                    console.print("[yellow]⚠ Failed to create QC project[/yellow]")
            except Exception as push_err:
                console.print(f"[yellow]⚠ Push to QC failed: {push_err}[/yellow]")

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
                f"Fitness={variant.get('fitness', 0):.4f}"
            )
            if metrics:
                console.print(
                    f"     Sharpe={metrics.get('sharpe_ratio', 0):.2f}, "
                    f"Return={metrics.get('total_return', 0):.1%}, "
                    f"MaxDD={metrics.get('max_drawdown', 0):.1%}, "
                    f"CAGR={metrics.get('cagr', 0):.1%}, "
                    f"WinRate={metrics.get('win_rate', 0):.1%}, "
                    f"Trades={metrics.get('total_trades', 0)}"
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
@click.option('--evolve', is_flag=True, help='Evolve strategies after backtest passes')
@click.option('--gens', default=5, type=int, help='Evolution generations (with --evolve)')
@click.option('--variants', default=3, type=int, help='Variants per generation (with --evolve)')
@click.pass_context
def schedule_start(ctx, interval, hour, day, queries, min_sharpe, max_strategies,
                   notion_min_sharpe, output, run_now, evolve, gens, variants):
    """
    Start the automated scheduled pipeline.

    This runs the full workflow on a schedule:
    1. Search for new research papers
    2. Generate and backtest strategies
    3. Publish successful strategies to Notion
    4. Keep algorithms in QuantConnect

    With --evolve flag:
    - After each strategy passes backtest, evolves it for N generations
    - Publishes the best evolved variant to Notion

    Examples:
        quantcoder schedule start --interval daily --hour 6
        quantcoder schedule start --interval weekly --day mon --hour 9
        quantcoder schedule start --queries "momentum,mean reversion" --run-now
        quantcoder schedule start --evolve --gens 5  # With evolution
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
        evolve_strategies=evolve,
        evolution_generations=gens,
        evolution_variants=variants,
    )

    if search_queries:
        pipeline_config.search_queries = [q.strip() for q in search_queries]
    if output_dir:
        pipeline_config.output_dir = output_dir

    if evolve:
        console.print(f"[cyan]Evolution enabled: {gens} generations, {variants} variants/gen[/cyan]")

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
@click.option('--evolve', is_flag=True, help='Evolve strategies after backtest passes')
@click.option('--gens', default=5, type=int, help='Evolution generations (with --evolve)')
@click.option('--variants', default=3, type=int, help='Variants per generation (with --evolve)')
@click.pass_context
def schedule_run(ctx, queries, min_sharpe, max_strategies, output, evolve, gens, variants):
    """
    Run the automated pipeline once (no scheduling).

    Good for testing or manual runs.

    With --evolve flag:
    - After each strategy passes backtest, evolves it for N generations
    - Publishes the best evolved variant to Notion

    Examples:
        quantcoder schedule run
        quantcoder schedule run --queries "factor investing" --min-sharpe 1.0
        quantcoder schedule run --evolve --gens 5  # With evolution
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
        evolve_strategies=evolve,
        evolution_generations=gens,
        evolution_variants=variants,
    )

    if search_queries:
        pipeline_config.search_queries = [q.strip() for q in search_queries]
    if output_dir:
        pipeline_config.output_dir = output_dir

    if evolve:
        console.print(f"[cyan]Evolution enabled: {gens} generations, {variants} variants/gen[/cyan]")

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
@click.option('--tavily-key', help='Set Tavily API key for deep search')
@click.option('--show', is_flag=True, help='Show current configuration')
def schedule_config(notion_key, notion_db, tavily_key, show):
    """
    Configure scheduler settings (Notion, Tavily, etc.)

    Examples:
        quantcoder schedule config --show
        quantcoder schedule config --notion-key secret_xxx --notion-db abc123
        quantcoder schedule config --tavily-key tvly-xxx
    """
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    env_file = Path.home() / ".quantcoder" / ".env"

    # Load existing env vars
    if env_file.exists():
        load_dotenv(env_file)

    if show:
        console.print("\n[bold cyan]Integration Configuration[/bold cyan]\n")

        # Check Notion settings
        notion_key_set = bool(os.getenv('NOTION_API_KEY'))
        notion_db_set = bool(os.getenv('NOTION_DATABASE_ID'))
        tavily_key_set = bool(os.getenv('TAVILY_API_KEY'))

        console.print("[bold]Notion (article publishing):[/bold]")
        console.print(f"  NOTION_API_KEY: {'[green]Set[/green]' if notion_key_set else '[yellow]Not set[/yellow]'}")
        console.print(f"  NOTION_DATABASE_ID: {'[green]Set[/green]' if notion_db_set else '[yellow]Not set[/yellow]'}")

        console.print("\n[bold]Tavily (deep search):[/bold]")
        console.print(f"  TAVILY_API_KEY: {'[green]Set[/green]' if tavily_key_set else '[yellow]Not set[/yellow]'}")

        console.print(f"\n[dim]Environment file: {env_file}[/dim]")
        return

    if not notion_key and not notion_db and not tavily_key:
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

    if tavily_key:
        env_vars['TAVILY_API_KEY'] = tavily_key
        console.print("[green]Set TAVILY_API_KEY[/green]")

    # Write back
    env_file.parent.mkdir(parents=True, exist_ok=True)
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"\n[dim]Configuration saved to {env_file}[/dim]")


# ============================================================================
# LOGGING AND MONITORING COMMANDS
# ============================================================================

@main.group()
def logs():
    """
    View and manage logs.

    Commands to view log files, tail recent activity, and manage log rotation.
    """
    pass


@logs.command(name='show')
@click.option('--lines', '-n', default=50, type=int, help='Number of lines to show')
@click.option('--json', 'json_format', is_flag=True, help='Show JSON structured logs')
@click.pass_context
def logs_show(ctx, lines, json_format):
    """
    Show recent log entries.

    Examples:
        quantcoder logs show
        quantcoder logs show --lines 100
        quantcoder logs show --json
    """
    from quantcoder.logging_config import get_log_files

    config = ctx.obj['config']
    log_dir = config.home_dir / "logs"

    if json_format:
        log_file = log_dir / "quantcoder.json.log"
    else:
        log_file = log_dir / "quantcoder.log"

    if not log_file.exists():
        console.print(f"[yellow]No log file found at {log_file}[/yellow]")
        console.print("[dim]Logs will be created after running commands.[/dim]")
        return

    try:
        with open(log_file) as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines

        console.print(f"[cyan]Last {len(recent)} entries from {log_file.name}:[/cyan]\n")

        for line in recent:
            line = line.rstrip()
            if json_format:
                try:
                    import json
                    data = json.loads(line)
                    level = data.get('level', 'INFO')
                    color = {
                        'DEBUG': 'dim',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold red',
                    }.get(level, 'white')
                    console.print(f"[{color}]{data.get('timestamp', '')} | {level} | {data.get('message', '')}[/{color}]")
                except json.JSONDecodeError:
                    console.print(line)
            else:
                # Color based on log level
                if ' ERROR ' in line or ' CRITICAL ' in line:
                    console.print(f"[red]{line}[/red]")
                elif ' WARNING ' in line:
                    console.print(f"[yellow]{line}[/yellow]")
                elif ' DEBUG ' in line:
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(line)

    except Exception as e:
        console.print(f"[red]Error reading log file: {e}[/red]")


@logs.command(name='list')
@click.pass_context
def logs_list(ctx):
    """
    List all log files.

    Shows all log files with their sizes and modification times.
    """
    from rich.table import Table

    config = ctx.obj['config']
    log_dir = config.home_dir / "logs"

    if not log_dir.exists():
        console.print(f"[yellow]Log directory not found: {log_dir}[/yellow]")
        return

    log_files = sorted(log_dir.glob("quantcoder*.log*"))

    if not log_files:
        console.print("[yellow]No log files found.[/yellow]")
        return

    table = Table(title="Log Files")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Modified", style="dim")

    for log_file in log_files:
        size = log_file.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        from datetime import datetime
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")

        table.add_row(log_file.name, size_str, mtime_str)

    console.print(table)
    console.print(f"\n[dim]Log directory: {log_dir}[/dim]")


@logs.command(name='clear')
@click.option('--keep', default=1, type=int, help='Number of backup files to keep')
@click.confirmation_option(prompt='Are you sure you want to clear old log files?')
@click.pass_context
def logs_clear(ctx, keep):
    """
    Clear old log files.

    Keeps the most recent backup files and removes older ones.
    """
    config = ctx.obj['config']
    log_dir = config.home_dir / "logs"

    if not log_dir.exists():
        console.print("[yellow]No log directory found.[/yellow]")
        return

    # Find backup files (*.log.1, *.log.2, etc.)
    removed = 0
    for pattern in ["quantcoder.log.*", "quantcoder.json.log.*"]:
        backup_files = sorted(log_dir.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)

        for backup_file in backup_files[keep:]:
            try:
                backup_file.unlink()
                removed += 1
                console.print(f"[dim]Removed: {backup_file.name}[/dim]")
            except Exception as e:
                console.print(f"[red]Failed to remove {backup_file.name}: {e}[/red]")

    if removed:
        console.print(f"\n[green]Cleared {removed} old log file(s)[/green]")
    else:
        console.print("[dim]No old log files to clear[/dim]")


@logs.command(name='config')
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set log level')
@click.option('--format', 'log_format', type=click.Choice(['standard', 'json']),
              help='Set log format')
@click.option('--max-size', type=int, help='Max log file size in MB')
@click.option('--backups', type=int, help='Number of backup files to keep')
@click.option('--webhook', help='Webhook URL for error alerts')
@click.option('--show', is_flag=True, help='Show current logging configuration')
@click.pass_context
def logs_config(ctx, level, log_format, max_size, backups, webhook, show):
    """
    Configure logging settings.

    Examples:
        quantcoder logs config --show
        quantcoder logs config --level DEBUG
        quantcoder logs config --max-size 20 --backups 10
        quantcoder logs config --webhook https://hooks.slack.com/...
    """
    config = ctx.obj['config']

    if show:
        console.print("\n[bold cyan]Logging Configuration[/bold cyan]\n")
        console.print(f"  Level: [green]{config.logging.level}[/green]")
        console.print(f"  Format: [green]{config.logging.format}[/green]")
        console.print(f"  Max File Size: [green]{config.logging.max_file_size_mb} MB[/green]")
        console.print(f"  Backup Count: [green]{config.logging.backup_count}[/green]")
        console.print(f"  Alert on Error: [green]{config.logging.alert_on_error}[/green]")
        console.print(f"  Webhook URL: [green]{config.logging.webhook_url or 'Not set'}[/green]")
        console.print(f"\n  Log Directory: [dim]{config.home_dir / 'logs'}[/dim]")
        return

    updated = False

    if level:
        config.logging.level = level
        console.print(f"[green]Set log level: {level}[/green]")
        updated = True

    if log_format:
        config.logging.format = log_format
        console.print(f"[green]Set log format: {log_format}[/green]")
        updated = True

    if max_size:
        config.logging.max_file_size_mb = max_size
        console.print(f"[green]Set max file size: {max_size} MB[/green]")
        updated = True

    if backups:
        config.logging.backup_count = backups
        console.print(f"[green]Set backup count: {backups}[/green]")
        updated = True

    if webhook:
        config.logging.webhook_url = webhook
        config.logging.alert_on_error = True
        console.print(f"[green]Set webhook URL and enabled error alerts[/green]")
        updated = True

    if updated:
        config.save()
        console.print("\n[dim]Configuration saved. Restart quantcoder to apply changes.[/dim]")
    else:
        console.print("[yellow]No options provided. Use --show to see current config.[/yellow]")


if __name__ == '__main__':
    main()
