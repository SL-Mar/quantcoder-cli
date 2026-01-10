"""Interactive and programmatic chat interfaces for QuantCoder."""

import logging
from typing import List, Dict, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .config import Config
from .tools import (
    SearchArticlesTool,
    DownloadArticleTool,
    SummarizeArticleTool,
    GenerateCodeTool,
    ReadFileTool,
    WriteFileTool,
)

console = Console()
logger = logging.getLogger(__name__)


class InteractiveChat:
    """Interactive chat interface with conversational AI."""

    def __init__(self, config: Config):
        self.config = config
        self.context: List[Dict] = []
        self.session = PromptSession(
            history=FileHistory(str(config.home_dir / ".history")),
            auto_suggest=AutoSuggestFromHistory(),
        )

        # Initialize tools
        self.tools = {
            'search': SearchArticlesTool(config),
            'download': DownloadArticleTool(config),
            'summarize': SummarizeArticleTool(config),
            'generate': GenerateCodeTool(config),
            'read': ReadFileTool(config),
            'write': WriteFileTool(config),
        }

        # Command completions
        self.completer = WordCompleter(
            ['help', 'exit', 'quit', 'search', 'download', 'summarize',
             'generate', 'config', 'clear', 'history'],
            ignore_case=True
        )

    def run(self):
        """Run the interactive chat loop."""
        while True:
            try:
                # Get user input
                user_input = self.session.prompt(
                    "quantcoder> ",
                    completer=self.completer,
                    multiline=False
                ).strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[cyan]Goodbye![/cyan]")
                    break

                elif user_input.lower() == 'help':
                    self.show_help()
                    continue

                elif user_input.lower() == 'clear':
                    console.clear()
                    continue

                elif user_input.lower() == 'config':
                    self.show_config()
                    continue

                # Process the input
                self.process_input(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' or 'quit' to leave[/yellow]")
                continue

            except EOFError:
                break

    def process_input(self, user_input: str):
        """Process user input and execute appropriate actions."""

        # Parse input for tool invocation
        if user_input.startswith('search '):
            query = user_input[7:].strip()
            self.execute_tool('search', query=query, max_results=5)

        elif user_input.startswith('download '):
            try:
                article_id = int(user_input[9:].strip())
                self.execute_tool('download', article_id=article_id)
            except ValueError:
                console.print("[red]Error: Please provide a valid article ID[/red]")

        elif user_input.startswith('summarize '):
            try:
                article_id = int(user_input[10:].strip())
                self.execute_tool('summarize', article_id=article_id)
            except ValueError:
                console.print("[red]Error: Please provide a valid article ID[/red]")

        elif user_input.startswith('generate '):
            try:
                article_id = int(user_input[9:].strip())
                self.execute_tool('generate', article_id=article_id, max_refine_attempts=6)
            except ValueError:
                console.print("[red]Error: Please provide a valid article ID[/red]")

        else:
            # For natural language queries, use the LLM to interpret
            self.process_natural_language(user_input)

    def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool with given parameters."""
        tool = self.tools.get(tool_name)

        if not tool:
            console.print(f"[red]Error: Tool '{tool_name}' not found[/red]")
            return

        # Show what we're doing
        console.print(f"[cyan]→[/cyan] Executing: {tool_name}")

        # Execute with status indicator
        with console.status(f"[cyan]Running {tool_name}...[/cyan]"):
            result = tool.execute(**kwargs)

        # Display result
        if result.success:
            console.print(f"[green]✓[/green] {result.message}")

            # Special handling for different tools
            if tool_name == 'search' and result.data:
                for idx, article in enumerate(result.data, 1):
                    published = f" ({article['published']})" if article.get('published') else ""
                    console.print(
                        f"  [cyan]{idx}.[/cyan] {article['title']}\n"
                        f"      [dim]{article['authors']}{published}[/dim]"
                    )

            elif tool_name == 'summarize' and result.data:
                console.print(Panel(
                    Markdown(result.data['summary']),
                    title="Summary",
                    border_style="green"
                ))

            elif tool_name == 'generate' and result.data:
                # Display summary if available
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
                    theme=self.config.ui.theme,
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

    def process_natural_language(self, user_input: str):
        """Process natural language input using LLM."""
        from .core.llm import LLMHandler

        console.print("[cyan]→[/cyan] Processing natural language query...")

        llm = LLMHandler(self.config)

        # Build context with system prompt
        messages = [{
            "role": "system",
            "content": (
                "You are QuantCoder, an AI assistant specialized in helping users "
                "generate QuantConnect trading algorithms from research articles. "
                "You can help users search for articles, download PDFs, summarize "
                "trading strategies, and generate Python code. "
                "Be concise and helpful. If users ask about trading strategies, "
                "guide them through the process: search → download → summarize → generate."
            )
        }]

        # Add conversation history
        messages.extend(self.context)

        # Add current message
        messages.append({"role": "user", "content": user_input})

        # Get response
        response = llm.chat(user_input, context=messages)

        if response:
            # Update context
            self.context.append({"role": "user", "content": user_input})
            self.context.append({"role": "assistant", "content": response})

            # Keep context manageable (last 10 exchanges)
            if len(self.context) > 20:
                self.context = self.context[-20:]

            # Display response
            console.print(Panel(
                Markdown(response),
                title="QuantCoder",
                border_style="cyan"
            ))
        else:
            console.print("[red]Error: Failed to get response from LLM[/red]")

    def show_help(self):
        """Show help information."""
        help_text = """
# QuantCoder Commands

## Direct Commands:
- `search <query>` - Search for articles
- `download <id>` - Download article PDF
- `summarize <id>` - Summarize article strategy
- `generate <id>` - Generate QuantConnect code
- `config` - Show configuration
- `clear` - Clear screen
- `help` - Show this help
- `exit` / `quit` - Exit the program

## Natural Language:
You can also ask questions in natural language, such as:
- "Find articles about momentum trading"
- "How do I generate code from an article?"
- "What's the difference between mean reversion and momentum?"

## Workflow:
1. Search for articles: `search "algorithmic trading"`
2. Download an article: `download 1`
3. Summarize the strategy: `summarize 1`
4. Generate code: `generate 1`
"""

        console.print(Panel(
            Markdown(help_text),
            title="Help",
            border_style="cyan"
        ))

    def show_config(self):
        """Show current configuration."""
        config_text = f"""
**Model:** {self.config.model.model}
**Temperature:** {self.config.model.temperature}
**Theme:** {self.config.ui.theme}
**Downloads:** {self.config.tools.downloads_dir}
**Generated Code:** {self.config.tools.generated_code_dir}
"""

        console.print(Panel(
            Markdown(config_text),
            title="Configuration",
            border_style="cyan"
        ))


class ProgrammaticChat:
    """Non-interactive chat for programmatic usage."""

    def __init__(self, config: Config):
        self.config = config
        self.config.ui.auto_approve = True  # Always auto-approve in programmatic mode

        # Initialize tools
        self.tools = {
            'search': SearchArticlesTool(config),
            'download': DownloadArticleTool(config),
            'summarize': SummarizeArticleTool(config),
            'generate': GenerateCodeTool(config),
            'read': ReadFileTool(config),
            'write': WriteFileTool(config),
        }

    def process(self, prompt: str) -> str:
        """Process a single prompt and return the result."""
        from .core.llm import LLMHandler

        logger.info(f"Processing programmatic prompt: {prompt}")

        llm = LLMHandler(self.config)

        # Build context with system prompt
        messages = [{
            "role": "system",
            "content": (
                "You are QuantCoder, an AI assistant specialized in helping users "
                "generate QuantConnect trading algorithms from research articles. "
                "Provide concise, actionable responses."
            )
        }, {
            "role": "user",
            "content": prompt
        }]

        response = llm.chat(prompt, context=messages)

        if response:
            return response
        else:
            return "Error: Failed to process prompt"
