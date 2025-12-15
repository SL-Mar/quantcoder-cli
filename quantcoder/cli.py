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


if __name__ == '__main__':
    main()
