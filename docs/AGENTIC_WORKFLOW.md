# Understanding the Agentic Workflow in QuantCoder CLI v2.0

> A deep dive into the tool-based, agent-inspired architecture

**Author:** Technical Documentation
**Date:** December 2025
**Version:** 2.0

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is an Agentic Workflow?](#what-is-an-agentic-workflow)
3. [Architecture Overview](#architecture-overview)
4. [Core Components Deep Dive](#core-components-deep-dive)
5. [Tool System Internals](#tool-system-internals)
6. [Execution Flow](#execution-flow)
7. [Chat Interface & Context Management](#chat-interface--context-management)
8. [Configuration System](#configuration-system)
9. [Code Walkthrough: End-to-End Example](#code-walkthrough-end-to-end-example)
10. [Comparison: Traditional vs Agentic](#comparison-traditional-vs-agentic)
11. [Extending the System](#extending-the-system)

---

## Introduction

QuantCoder CLI v2.0 represents a paradigm shift from traditional script-based automation to an **agentic workflow** architecture. Inspired by Mistral's Vibe CLI, this refactoring introduces concepts from autonomous agent systems into a practical CLI tool.

This article explains:
- How the agent architecture is structured
- How tools enable modular, composable operations
- How LLMs orchestrate tool execution
- How the system maintains context and state
- How you can extend it with custom tools

---

## What is an Agentic Workflow?

### Traditional CLI Workflow

```python
# Traditional approach: Direct function calls
def main():
    articles = search_crossref("momentum trading")
    article = download_pdf(articles[0])
    summary = extract_and_summarize(article)
    code = generate_quantconnect_code(summary)
    save_code(code)
```

**Problems:**
- Tight coupling between components
- No flexibility in execution order
- Hard to extend with new capabilities
- No intelligent decision-making
- User must know exact command sequence

### Agentic Workflow

```python
# Agentic approach: Tool-based with AI orchestration
class Agent:
    def __init__(self, tools, llm):
        self.tools = tools
        self.llm = llm

    def execute(self, user_intent):
        # AI decides which tools to use and in what order
        plan = self.llm.plan(user_intent, self.tools)
        results = []
        for tool, params in plan:
            result = self.tools[tool].execute(**params)
            results.append(result)
        return self.llm.synthesize(results)
```

**Benefits:**
- Tools are independent, composable units
- AI orchestrates tool execution based on context
- Natural language interface
- Easy to add new tools without changing core logic
- System adapts to user needs

---

## Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                          │
│              (Natural Language or Commands)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                          │
│                    (quantcoder/cli.py)                      │
│  • Command parsing                                          │
│  • Rich UI rendering                                        │
│  • Interactive/Programmatic modes                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chat Interface                           │
│                   (quantcoder/chat.py)                      │
│  • Conversation management                                  │
│  • Context tracking                                         │
│  • Intent interpretation                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Handler                            │
│                  (quantcoder/core/llm.py)                   │
│  • OpenAI API integration                                   │
│  • Prompt engineering                                       │
│  • Response parsing                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tool System                            │
│                  (quantcoder/tools/*.py)                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Article Tools│  │  Code Tools  │  │  File Tools  │    │
│  │              │  │              │  │              │    │
│  │ • search     │  │ • generate   │  │ • read       │    │
│  │ • download   │  │ • validate   │  │ • write      │    │
│  │ • summarize  │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Services                         │
│  • OpenAI API                                               │
│  • CrossRef API                                             │
│  • File System                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Patterns

1. **Tool Pattern**: Each capability is a self-contained tool
2. **Strategy Pattern**: Tools implement common interface
3. **Factory Pattern**: Tools are instantiated with configuration
4. **Chain of Responsibility**: Chat → LLM → Tools → Results
5. **Observer Pattern**: Rich UI updates based on tool execution

---

## Core Components Deep Dive

### 1. Configuration System (`quantcoder/config.py`)

The configuration system is the foundation of the agentic architecture.

```python
@dataclass
class Config:
    """Main configuration class for QuantCoder."""

    model: ModelConfig = field(default_factory=ModelConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    api_key: Optional[str] = None
    home_dir: Path = field(default_factory=lambda: Path.home() / ".quantcoder")
```

**Why this design?**

- **Dataclasses**: Automatic `__init__`, `__repr__`, type hints
- **Nested configs**: Logical grouping (model, UI, tools)
- **Defaults**: Sensible defaults with override capability
- **Serialization**: Easy TOML conversion via `to_dict()` / `from_dict()`

**How it enables agentic behavior:**

```python
# Tools can query configuration to determine behavior
class Tool:
    def is_enabled(self) -> bool:
        """Check if tool is enabled in configuration."""
        enabled = self.config.tools.enabled_tools
        disabled = self.config.tools.disabled_tools

        if self.name in disabled or "*" in disabled:
            return False

        if "*" in enabled or self.name in enabled:
            return True

        return False
```

This allows **dynamic tool discovery** - the agent only uses tools that are enabled in the config.

---

### 2. Tool Base Classes (`quantcoder/tools/base.py`)

The tool system is the heart of the agentic architecture.

#### Tool Result

```python
@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return self.message or f"Success: {self.data}"
        else:
            return self.error or "Unknown error"
```

**Design principles:**

- **Uniform interface**: All tools return same type
- **Success/failure handling**: Explicit success flag
- **Flexible data**: `Any` type allows diverse outputs
- **Human-readable**: `__str__` for display

#### Tool Abstract Base Class

```python
class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, config: Any):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
```

**Why abstract base class?**

- **Contract enforcement**: All tools must implement name, description, execute
- **Polymorphism**: Tools can be used interchangeably
- **Documentation**: Self-documenting via description property
- **Type safety**: Ensures consistent API

**Agent perspective:**

From the agent's view, all tools look the same:

```python
def use_tool(tool_name: str, **params):
    tool = tools[tool_name]

    # Agent only needs to know:
    # 1. Tool name (for selection)
    # 2. Tool description (for understanding capability)
    # 3. Execute method (for invocation)

    result = tool.execute(**params)

    if result.success:
        return result.data
    else:
        handle_error(result.error)
```

---

### 3. Tool Implementation Example

Let's analyze `SearchArticlesTool` in detail:

```python
class SearchArticlesTool(Tool):
    """Tool for searching academic articles using CrossRef API."""

    @property
    def name(self) -> str:
        return "search_articles"

    @property
    def description(self) -> str:
        return "Search for academic articles using CrossRef API"

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """
        Search for articles using CrossRef API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            ToolResult with list of articles
        """
        self.logger.info(f"Searching for articles: {query}")

        try:
            articles = self._search_crossref(query, rows=max_results)

            if not articles:
                return ToolResult(
                    success=False,
                    error="No articles found or an error occurred during the search"
                )

            # Save articles to cache
            cache_file = Path(self.config.home_dir) / "articles.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_file, 'w') as f:
                json.dump(articles, f, indent=4)

            return ToolResult(
                success=True,
                data=articles,
                message=f"Found {len(articles)} articles"
            )

        except Exception as e:
            self.logger.error(f"Error searching articles: {e}")
            return ToolResult(success=False, error=str(e))
```

**Key design patterns:**

1. **Single Responsibility**: Tool only searches, doesn't display or process
2. **Error Handling**: Graceful degradation with error messages
3. **State Management**: Saves results to cache for other tools
4. **Logging**: Comprehensive logging for debugging
5. **Configuration Access**: Uses `self.config` for paths

**Agentic implications:**

```python
# Agent can chain tools naturally:
search_result = search_tool.execute(query="momentum trading")
if search_result.success:
    # Articles are cached, download tool can access them
    download_result = download_tool.execute(article_id=1)
    if download_result.success:
        # Downloaded file location is known, summarize tool can use it
        summarize_result = summarize_tool.execute(article_id=1)
```

Tools form a **dependency graph** where outputs of one tool become inputs to another.

---

### 4. LLM Handler (`quantcoder/core/llm.py`)

The LLM Handler is the "brain" of the agent.

```python
class LLMHandler:
    """Handles interactions with the OpenAI API."""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize OpenAI client with new SDK
        api_key = config.api_key or config.load_api_key()
        self.client = OpenAI(api_key=api_key)
        self.model = config.model.model
        self.temperature = config.model.temperature
        self.max_tokens = config.model.max_tokens
```

**Key methods:**

#### 1. Generate Summary

```python
def generate_summary(self, extracted_data: Dict[str, List[str]]) -> Optional[str]:
    """Generate a summary of the trading strategy and risk management."""

    trading_signals = '\n'.join(extracted_data.get('trading_signal', []))
    risk_management = '\n'.join(extracted_data.get('risk_management', []))

    prompt = f"""Provide a clear and concise summary of the following trading strategy...

    ### Trading Strategy Overview:
    {trading_signals}

    ### Risk Management Rules:
    {risk_management}
    """

    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an algorithmic trading expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        self.logger.error(f"Error during summary generation: {e}")
        return None
```

**Prompt engineering patterns:**

- **System prompt**: Sets role/context ("You are an algorithmic trading expert")
- **Structured prompt**: Clear sections (Trading Strategy, Risk Management)
- **Instructions**: Explicit formatting requirements
- **Temperature control**: Lower for deterministic tasks (code), higher for creative tasks

#### 2. Chat Method (Agentic Core)

```python
def chat(self, message: str, context: Optional[List[Dict]] = None) -> Optional[str]:
    """
    Have a chat conversation with the LLM.

    Args:
        message: User message
        context: Optional conversation history

    Returns:
        LLM response or None if chat failed
    """
    self.logger.info("Chatting with LLM")

    messages = context or []
    messages.append({"role": "user", "content": message})

    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        self.logger.error(f"Error during chat: {e}")
        return None
```

**Context management:**

The `context` parameter enables **multi-turn conversations**:

```python
context = [
    {"role": "system", "content": "You are a trading expert..."},
    {"role": "user", "content": "What is momentum trading?"},
    {"role": "assistant", "content": "Momentum trading is..."},
    {"role": "user", "content": "How do I implement it?"},  # Understands "it" refers to momentum
]
```

---

### 5. Chat Interface (`quantcoder/chat.py`)

The chat interface orchestrates the interaction between user, LLM, and tools.

#### Interactive Chat Class

```python
class InteractiveChat:
    """Interactive chat interface with conversational AI."""

    def __init__(self, config: Config):
        self.config = config
        self.context: List[Dict] = []  # Conversation history
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
```

**Design highlights:**

- **Context persistence**: `self.context` maintains conversation state
- **History**: Uses `FileHistory` for command history across sessions
- **Auto-suggest**: Learns from history to suggest commands
- **Tool registry**: Dictionary of available tools

#### Main Loop

```python
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

            # Process the input
            self.process_input(user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' or 'quit' to leave[/yellow]")
            continue
```

**REPL pattern (Read-Eval-Print Loop):**

1. **Read**: Get user input via `prompt()`
2. **Eval**: Process via `process_input()`
3. **Print**: Display results via Rich console
4. **Loop**: Repeat until exit

#### Input Processing

```python
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

    # ... other direct commands ...

    else:
        # For natural language queries, use the LLM to interpret
        self.process_natural_language(user_input)
```

**Two-tier input handling:**

1. **Direct commands**: Pattern matching for efficiency (`search ...`, `download ...`)
2. **Natural language**: Fallback to LLM for interpretation

#### Natural Language Processing

```python
def process_natural_language(self, user_input: str):
    """Process natural language input using LLM."""
    from .core.llm import LLMHandler

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
```

**Agentic workflow in action:**

1. **Intent understanding**: LLM interprets vague user input
2. **Tool recommendation**: LLM suggests tools to use
3. **Context awareness**: Previous conversation informs current response
4. **Graceful guidance**: LLM guides users through multi-step workflows

---

## Tool System Internals

### Tool Lifecycle

```
1. Instantiation
   ↓
   Tool(config) → __init__()

2. Registration
   ↓
   tools = {'search': SearchArticlesTool(config), ...}

3. Selection
   ↓
   tool = tools[tool_name]

4. Validation
   ↓
   if tool.is_enabled() and approved():

5. Execution
   ↓
   result = tool.execute(**params)

6. Result Handling
   ↓
   if result.success:
       process(result.data)
   else:
       handle_error(result.error)
```

### Tool Composition

Tools can be composed to create complex workflows:

```python
def workflow_generate_from_search(query: str):
    """Compose multiple tools into a workflow."""

    # Step 1: Search
    search_result = tools['search'].execute(query=query, max_results=5)
    if not search_result.success:
        return f"Search failed: {search_result.error}"

    # Step 2: Download first article
    download_result = tools['download'].execute(article_id=1)
    if not download_result.success:
        return f"Download failed: {download_result.error}"

    # Step 3: Summarize
    summarize_result = tools['summarize'].execute(article_id=1)
    if not summarize_result.success:
        return f"Summarize failed: {summarize_result.error}"

    # Step 4: Generate code
    generate_result = tools['generate'].execute(article_id=1)
    if not generate_result.success:
        return f"Generate failed: {generate_result.error}"

    return generate_result.data['code']
```

**This is exactly what the LLM does implicitly!**

When a user says "Find and code a momentum strategy", the LLM understands this requires:
1. Search for momentum articles
2. Download one
3. Summarize the strategy
4. Generate code

---

## Execution Flow

### End-to-End Flow Diagram

```
User: "Generate code from momentum trading article"
  │
  ├─→ CLI: Parse command / detect natural language
  │
  ├─→ Chat: Route to appropriate handler
  │     │
  │     ├─→ Direct command? → Execute tool directly
  │     │
  │     └─→ Natural language? → Send to LLM
  │           │
  │           └─→ LLM: Understand intent
  │                 │
  │                 ├─→ Generate response plan
  │                 │
  │                 └─→ Recommend tools/steps
  │
  ├─→ Tool Executor: Execute recommended tools
  │     │
  │     ├─→ SearchArticlesTool.execute(query="momentum trading")
  │     │     │
  │     │     ├─→ Call CrossRef API
  │     │     │
  │     │     └─→ Save to cache → ToolResult(success=True, data=[...])
  │     │
  │     ├─→ DownloadArticleTool.execute(article_id=1)
  │     │     │
  │     │     ├─→ Read from cache
  │     │     │
  │     │     ├─→ Download PDF
  │     │     │
  │     │     └─→ Save to downloads/ → ToolResult(success=True, data="path/to/pdf")
  │     │
  │     ├─→ SummarizeArticleTool.execute(article_id=1)
  │     │     │
  │     │     ├─→ Read PDF from downloads/
  │     │     │
  │     │     ├─→ Extract text with pdfplumber
  │     │     │
  │     │     ├─→ Process with NLP (spaCy)
  │     │     │
  │     │     ├─→ Call LLM for summary
  │     │     │
  │     │     └─→ Save summary → ToolResult(success=True, data={summary: "..."})
  │     │
  │     └─→ GenerateCodeTool.execute(article_id=1)
  │           │
  │           ├─→ Read summary
  │           │
  │           ├─→ Call LLM for code generation
  │           │
  │           ├─→ Validate syntax (AST)
  │           │
  │           ├─→ Refine if needed (retry loop)
  │           │
  │           └─→ Save code → ToolResult(success=True, data={code: "..."})
  │
  └─→ UI: Display results with Rich
        │
        ├─→ Syntax highlight code
        │
        ├─→ Render markdown summary
        │
        └─→ Show success message
```

---

## Chat Interface & Context Management

### Context as Cognitive Memory

The conversation context acts as the agent's "short-term memory":

```python
self.context = [
    {
        "role": "system",
        "content": "You are QuantCoder, specialized in..."
    },
    {
        "role": "user",
        "content": "What is momentum trading?"
    },
    {
        "role": "assistant",
        "content": "Momentum trading is a strategy that..."
    },
    {
        "role": "user",
        "content": "Can you find articles about it?"  # "it" = momentum trading
    },
    {
        "role": "assistant",
        "content": "I'll search for momentum trading articles..."
    }
]
```

**Context enables:**

1. **Anaphora resolution**: Understanding "it", "that", "them"
2. **Continuity**: Maintaining thread across turns
3. **Learning**: Adapting to user preferences
4. **Disambiguation**: Using past context to clarify

### Context Pruning

To prevent context from growing indefinitely:

```python
# Keep context manageable (last 10 exchanges)
if len(self.context) > 20:
    self.context = self.context[-20:]
```

**Trade-offs:**

- **Too much context**: Higher costs, slower responses, potential confusion
- **Too little context**: Loss of continuity, repetitive questions
- **Optimal**: Last 10-20 turns balances memory and efficiency

---

## Configuration System

### Configuration as Agent Behavior Control

The configuration system controls how the agent behaves:

```toml
[model]
provider = "openai"
model = "gpt-4o-2024-11-20"
temperature = 0.5      # Lower = more deterministic
max_tokens = 2000      # Longer responses

[ui]
theme = "monokai"
auto_approve = false   # Require approval for tool execution
show_token_usage = true

[tools]
enabled_tools = ["*"]              # Enable all tools
disabled_tools = ["write_file"]    # Except file writing
downloads_dir = "downloads"
generated_code_dir = "generated_code"
```

### Dynamic Tool Enabling

```python
class Tool:
    def is_enabled(self) -> bool:
        """Check if tool is enabled in configuration."""
        enabled = self.config.tools.enabled_tools
        disabled = self.config.tools.disabled_tools

        # Explicit disable takes precedence
        if self.name in disabled or "*" in disabled:
            return False

        # Check if enabled
        if "*" in enabled or self.name in enabled:
            return True

        return False
```

**Use cases:**

- **Safety**: Disable destructive tools (`write_file`, `execute_shell`)
- **Sandboxing**: Only allow read-only tools
- **Specialization**: Enable only trading-related tools
- **Development**: Enable debug tools in dev mode

---

## Code Walkthrough: End-to-End Example

Let's trace a complete execution: **"Generate code for momentum trading"**

### Step 1: User Input

```python
# User types in terminal
quantcoder> search momentum trading
```

### Step 2: CLI Processing (`cli.py`)

```python
@main.command()
@click.argument('query')
@click.option('--num', default=5)
@click.pass_context
def search(ctx, query, num):
    """Search for academic articles on CrossRef."""
    config = ctx.obj['config']
    tool = SearchArticlesTool(config)  # Instantiate tool

    with console.status(f"Searching for '{query}'..."):
        result = tool.execute(query=query, max_results=num)  # Execute

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
        for idx, article in enumerate(result.data, 1):
            console.print(f"  [cyan]{idx}.[/cyan] {article['title']}")
    else:
        console.print(f"[red]✗[/red] {result.error}")
```

### Step 3: Tool Execution (`article_tools.py`)

```python
class SearchArticlesTool(Tool):
    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        self.logger.info(f"Searching for articles: {query}")

        try:
            # Call external API
            articles = self._search_crossref(query, rows=max_results)

            if not articles:
                return ToolResult(
                    success=False,
                    error="No articles found"
                )

            # Save to cache (state management)
            cache_file = Path(self.config.home_dir) / "articles.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_file, 'w') as f:
                json.dump(articles, f, indent=4)

            # Return success
            return ToolResult(
                success=True,
                data=articles,
                message=f"Found {len(articles)} articles"
            )

        except Exception as e:
            self.logger.error(f"Error searching articles: {e}")
            return ToolResult(success=False, error=str(e))

    def _search_crossref(self, query: str, rows: int = 5) -> List[Dict]:
        """Search CrossRef API for articles."""
        api_url = "https://api.crossref.org/works"
        params = {"query": query, "rows": rows}
        headers = {"User-Agent": "QuantCoder/2.0"}

        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Parse and format results
        articles = []
        for item in data.get('message', {}).get('items', []):
            article = {
                'title': item.get('title', ['No title'])[0],
                'authors': self._format_authors(item.get('author', [])),
                'DOI': item.get('DOI', ''),
                'URL': item.get('URL', '')
            }
            articles.append(article)

        return articles
```

### Step 4: User Downloads Article

```python
quantcoder> download 1
```

```python
# CLI calls DownloadArticleTool
class DownloadArticleTool(Tool):
    def execute(self, article_id: int) -> ToolResult:
        # Load cached articles (from previous search)
        cache_file = Path(self.config.home_dir) / "articles.json"
        with open(cache_file, 'r') as f:
            articles = json.load(f)

        article = articles[article_id - 1]

        # Download PDF
        save_path = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"
        success = self._download_pdf(article["URL"], save_path)

        if success:
            return ToolResult(
                success=True,
                data=str(save_path),
                message=f"Downloaded to {save_path}"
            )
        else:
            return ToolResult(success=False, error="Download failed")
```

### Step 5: Summarize Article

```python
quantcoder> summarize 1
```

```python
class SummarizeArticleTool(Tool):
    def execute(self, article_id: int) -> ToolResult:
        from ..core.processor import ArticleProcessor

        filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

        # Process PDF
        processor = ArticleProcessor(self.config)
        extracted_data = processor.extract_structure(str(filepath))

        # extract_structure does:
        # 1. Load PDF with pdfplumber
        # 2. Preprocess text (remove URLs, noise)
        # 3. Detect headings with spaCy NLP
        # 4. Split into sections
        # 5. Extract trading signals and risk management via keyword analysis

        # Generate summary with LLM
        summary = processor.generate_summary(extracted_data)

        # Save summary
        summary_path = Path(self.config.tools.downloads_dir) / f"article_{article_id}_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(summary)

        return ToolResult(
            success=True,
            data={"summary": summary, "path": str(summary_path)},
            message=f"Summary saved to {summary_path}"
        )
```

### Step 6: Generate Code

```python
quantcoder> generate 1
```

```python
class GenerateCodeTool(Tool):
    def execute(self, article_id: int, max_refine_attempts: int = 6) -> ToolResult:
        from ..core.processor import ArticleProcessor

        filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

        processor = ArticleProcessor(self.config, max_refine_attempts=max_refine_attempts)
        results = processor.extract_structure_and_generate_code(str(filepath))

        summary = results.get("summary")
        code = results.get("code")

        # Save code
        code_path = Path(self.config.tools.generated_code_dir) / f"algorithm_{article_id}.py"
        code_path.parent.mkdir(parents=True, exist_ok=True)

        with open(code_path, 'w') as f:
            f.write(code)

        return ToolResult(
            success=True,
            data={"code": code, "summary": summary, "path": str(code_path)},
            message=f"Code generated at {code_path}"
        )
```

**Code generation flow:**

```python
# ArticleProcessor.extract_structure_and_generate_code()

# 1. Extract structure (same as summarize)
extracted_data = self.extract_structure(pdf_path)

# 2. Generate summary
summary = self.llm_handler.generate_summary(extracted_data)

# 3. Generate code from summary
qc_code = self.llm_handler.generate_qc_code(summary)

# 4. Validate and refine loop
attempt = 0
while not self._validate_code(qc_code) and attempt < max_refine_attempts:
    qc_code = self.llm_handler.refine_code(qc_code)
    if self._validate_code(qc_code):
        break
    attempt += 1

return {"summary": summary, "code": qc_code}
```

**Self-healing code generation:**

The agent automatically refines invalid code up to 6 times:

```python
def _validate_code(self, code: str) -> bool:
    """Validate code syntax."""
    try:
        ast.parse(code)  # Try to parse as Python AST
        return True
    except SyntaxError:
        return False

# If validation fails:
# 1. Call LLM with error message
# 2. Ask it to fix the code
# 3. Validate again
# 4. Repeat until valid or max attempts
```

This is a form of **self-reflection** - the agent checks its own output and corrects mistakes.

---

## Comparison: Traditional vs Agentic

### Traditional CLI (v0.3)

```python
# quantcli/cli.py (legacy)

@cli.command()
def interactive():
    """Perform an interactive search and process with a GUI."""
    click.echo("Starting interactive mode...")
    launch_gui()  # Launches Tkinter GUI
```

**Problems:**

- Monolithic GUI application
- No modularity
- Can't compose operations
- No natural language
- Hard to extend

### Agentic CLI (v2.0)

```python
# quantcoder/cli.py (v2.0)

@main.group(invoke_without_command=True)
@click.pass_context
def main(ctx, verbose, config, prompt):
    """AI-powered CLI for generating QuantConnect algorithms."""

    # If prompt is provided, run in non-interactive mode
    if prompt:
        chat = ProgrammaticChat(cfg)
        result = chat.process(prompt)
        console.print(result)
        return

    # If no subcommand, launch interactive mode
    if ctx.invoked_subcommand is None:
        interactive(cfg)
```

**Benefits:**

- Programmatic mode (`--prompt`)
- Interactive chat mode
- Direct commands
- Tool composition
- Natural language
- Extensible

### Feature Comparison Table

| Feature | Traditional (v0.3) | Agentic (v2.0) |
|---------|-------------------|----------------|
| **Interface** | Tkinter GUI | CLI + Rich UI |
| **Input** | Buttons/Forms | Natural language + Commands |
| **Modularity** | Monolithic | Tool-based |
| **Extensibility** | Modify core code | Add new tools |
| **Automation** | Manual steps | `--prompt` flag |
| **Context** | None | Conversation history |
| **Error Handling** | Show error dialog | Self-healing loops |
| **Configuration** | Hardcoded | TOML config |
| **Composition** | Sequential only | Arbitrary tool chains |
| **AI Integration** | Fixed prompts | Adaptive prompts |

---

## Extending the System

### Adding a New Tool

Let's add a `BacktestTool` that backtests generated algorithms.

#### Step 1: Create Tool Class

```python
# quantcoder/tools/backtest_tools.py

from .base import Tool, ToolResult
import subprocess
from pathlib import Path

class BacktestTool(Tool):
    """Tool for backtesting QuantConnect algorithms."""

    @property
    def name(self) -> str:
        return "backtest"

    @property
    def description(self) -> str:
        return "Backtest a QuantConnect algorithm using LEAN engine"

    def execute(self, algorithm_path: str, start_date: str, end_date: str) -> ToolResult:
        """
        Backtest an algorithm.

        Args:
            algorithm_path: Path to algorithm .py file
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            ToolResult with backtest results
        """
        self.logger.info(f"Backtesting {algorithm_path}")

        try:
            # Call LEAN CLI
            result = subprocess.run([
                'lean', 'backtest',
                '--algorithm', algorithm_path,
                '--start', start_date,
                '--end', end_date
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Parse results
                results = self._parse_backtest_output(result.stdout)

                return ToolResult(
                    success=True,
                    data=results,
                    message=f"Backtest complete. Sharpe: {results['sharpe']}"
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Backtest failed: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Backtest timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _parse_backtest_output(self, output: str) -> dict:
        """Parse LEAN backtest output."""
        # Implementation to extract metrics
        return {
            'sharpe': 1.5,
            'total_return': 0.25,
            'max_drawdown': -0.10
        }
```

#### Step 2: Register Tool

```python
# quantcoder/tools/__init__.py

from .backtest_tools import BacktestTool

__all__ = [
    # ... existing tools ...
    "BacktestTool",
]
```

#### Step 3: Add to Chat Interface

```python
# quantcoder/chat.py

class InteractiveChat:
    def __init__(self, config: Config):
        # ... existing code ...

        self.tools = {
            'search': SearchArticlesTool(config),
            'download': DownloadArticleTool(config),
            'summarize': SummarizeArticleTool(config),
            'generate': GenerateCodeTool(config),
            'backtest': BacktestTool(config),  # New tool
            'read': ReadFileTool(config),
            'write': WriteFileTool(config),
        }
```

#### Step 4: Add CLI Command

```python
# quantcoder/cli.py

@main.command()
@click.argument('algorithm_path')
@click.option('--start', default='2020-01-01')
@click.option('--end', default='2023-12-31')
@click.pass_context
def backtest(ctx, algorithm_path, start, end):
    """Backtest a QuantConnect algorithm."""
    config = ctx.obj['config']
    tool = BacktestTool(config)

    with console.status(f"Backtesting {algorithm_path}..."):
        result = tool.execute(
            algorithm_path=algorithm_path,
            start_date=start,
            end_date=end
        )

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
        # Display metrics table
        from rich.table import Table
        table = Table(title="Backtest Results")
        table.add_column("Metric")
        table.add_column("Value")
        for key, value in result.data.items():
            table.add_row(key, str(value))
        console.print(table)
    else:
        console.print(f"[red]✗[/red] {result.error}")
```

#### Step 5: Update LLM System Prompt

```python
# quantcoder/chat.py

messages = [{
    "role": "system",
    "content": (
        "You are QuantCoder, an AI assistant specialized in helping users "
        "generate QuantConnect trading algorithms from research articles. "
        "You can help users search for articles, download PDFs, summarize "
        "trading strategies, generate Python code, and backtest algorithms. "  # Added backtest
        "Guide them through: search → download → summarize → generate → backtest."
    )
}]
```

Now users can:

```bash
# Direct command
quantcoder backtest generated_code/algorithm_1.py --start 2020-01-01 --end 2023-12-31

# Or natural language
quantcoder> Can you backtest the algorithm from article 1?
```

The LLM will understand to:
1. Find the generated code for article 1
2. Call the backtest tool with appropriate parameters
3. Present the results

### Adding Custom Agents

You can create specialized agents for specific workflows:

```python
# quantcoder/agents/trading_agent.py

class TradingAgent:
    """Specialized agent for trading strategy workflows."""

    def __init__(self, config, tools):
        self.config = config
        self.tools = tools
        self.llm = LLMHandler(config)

    def research_and_implement(self, strategy_name: str) -> dict:
        """
        Autonomous workflow: Research → Implement → Backtest

        Args:
            strategy_name: Name of strategy to research

        Returns:
            dict with code, backtest results, and report
        """
        # Step 1: Search
        search_result = self.tools['search'].execute(
            query=f"{strategy_name} trading strategy",
            max_results=10
        )

        # Step 2: Use LLM to pick best article
        article_summaries = [
            f"{i+1}. {a['title']}"
            for i, a in enumerate(search_result.data)
        ]

        prompt = f"""Which article is most relevant for implementing a {strategy_name} strategy?

        Articles:
        {chr(10).join(article_summaries)}

        Respond with just the number."""

        response = self.llm.chat(prompt)
        article_id = int(response.strip())

        # Step 3: Download
        self.tools['download'].execute(article_id=article_id)

        # Step 4: Generate code
        code_result = self.tools['generate'].execute(article_id=article_id)

        # Step 5: Backtest
        backtest_result = self.tools['backtest'].execute(
            algorithm_path=code_result.data['path'],
            start_date='2020-01-01',
            end_date='2023-12-31'
        )

        # Step 6: Generate report
        report = self._generate_report(
            strategy_name,
            code_result.data['summary'],
            backtest_result.data
        )

        return {
            'code': code_result.data['code'],
            'backtest': backtest_result.data,
            'report': report
        }
```

Usage:

```python
# In CLI
agent = TradingAgent(config, tools)
result = agent.research_and_implement("momentum")

console.print(result['report'])
```

---

## Advanced Agentic Patterns

### 1. Tool Chaining

Tools can automatically chain based on dependencies:

```python
class ToolChain:
    """Automatically chains tools based on dependencies."""

    def __init__(self, tools):
        self.tools = tools
        self.dependency_graph = self._build_graph()

    def _build_graph(self):
        """Build dependency graph from tool signatures."""
        # Example: GenerateTool depends on SummarizeTool
        # SummarizeTool depends on DownloadTool
        # DownloadTool depends on SearchTool
        return {
            'generate': ['summarize'],
            'summarize': ['download'],
            'download': ['search']
        }

    def execute_with_dependencies(self, tool_name: str, **params):
        """Execute tool and all its dependencies."""
        # Topological sort to determine execution order
        order = self._topological_sort(tool_name)

        results = {}
        for tool in order:
            # Get params from previous results if needed
            tool_params = self._resolve_params(tool, params, results)
            result = self.tools[tool].execute(**tool_params)
            results[tool] = result

        return results[tool_name]
```

### 2. Conditional Execution

Tools can decide whether to execute based on state:

```python
class ConditionalTool(Tool):
    """Tool that only executes if conditions are met."""

    def execute(self, **kwargs) -> ToolResult:
        # Check preconditions
        if not self._check_preconditions(**kwargs):
            return ToolResult(
                success=False,
                error="Preconditions not met"
            )

        # Execute actual logic
        return self._execute_impl(**kwargs)

    def _check_preconditions(self, **kwargs) -> bool:
        """Override in subclasses."""
        return True
```

### 3. Parallel Execution

Execute multiple independent tools concurrently:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelExecutor:
    """Execute multiple tools in parallel."""

    def __init__(self, tools):
        self.tools = tools
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def execute_parallel(self, tool_calls: List[Tuple[str, dict]]):
        """Execute multiple tool calls in parallel."""
        tasks = [
            asyncio.create_task(self._execute_async(tool, params))
            for tool, params in tool_calls
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def _execute_async(self, tool_name: str, params: dict):
        """Execute a single tool asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.tools[tool_name].execute,
            **params
        )

# Usage:
executor = ParallelExecutor(tools)
results = await executor.execute_parallel([
    ('search', {'query': 'momentum'}),
    ('search', {'query': 'mean reversion'}),
    ('search', {'query': 'pairs trading'})
])
```

### 4. Retry Logic

Automatically retry failed tool executions:

```python
def retry_tool(tool: Tool, max_attempts: int = 3, **kwargs) -> ToolResult:
    """Retry tool execution on failure."""

    for attempt in range(max_attempts):
        result = tool.execute(**kwargs)

        if result.success:
            return result

        if attempt < max_attempts - 1:
            # Exponential backoff
            sleep_time = 2 ** attempt
            time.sleep(sleep_time)
            logger.info(f"Retrying {tool.name} (attempt {attempt + 2}/{max_attempts})")

    return result  # Return last failed result
```

---

## Conclusion

The agentic workflow in QuantCoder CLI v2.0 represents a fundamental shift in how we build CLI tools:

### Key Takeaways

1. **Tools as Building Blocks**: Each capability is a self-contained, composable unit
2. **LLM as Orchestrator**: AI decides which tools to use and when
3. **Context as Memory**: Conversation history enables natural interactions
4. **Configuration as Behavior**: TOML files control agent capabilities
5. **Results as Data**: Uniform `ToolResult` interface enables chaining

### Architectural Benefits

- **Modularity**: Easy to add/remove/modify tools
- **Testability**: Each tool can be tested independently
- **Extensibility**: New workflows via tool composition
- **Flexibility**: Natural language + direct commands
- **Maintainability**: Clear separation of concerns

### Future Directions

- **Multi-agent systems**: Specialized agents for different tasks
- **Tool learning**: Agents learn which tools work best
- **Dynamic prompting**: Prompts adapt based on user behavior
- **MCP integration**: Connect to external tool servers
- **Function calling**: Use OpenAI's function calling for better tool selection

### Learning Resources

To deepen your understanding:

1. **Read the code**: Start with `quantcoder/tools/base.py`
2. **Trace execution**: Add logging to see tool flow
3. **Create custom tools**: Best way to learn is by building
4. **Study LLM prompts**: See how prompts guide behavior
5. **Explore Vibe CLI**: Compare with Mistral's implementation

### Final Thoughts

Agentic workflows represent the future of software development. By combining:
- **Modular tools** (what the system can do)
- **LLM intelligence** (how to use tools)
- **Natural language** (how users interact)

We create systems that are more powerful, flexible, and user-friendly than traditional approaches.

The code in QuantCoder v2.0 is a practical example of these principles in action. Study it, extend it, and apply these patterns to your own projects.

---

## Appendix: Complete Tool Template

```python
"""Template for creating new tools."""

from pathlib import Path
from typing import Any, Dict, Optional
from .base import Tool, ToolResult
import logging

class MyCustomTool(Tool):
    """
    Tool for [describe purpose].

    This tool [explain what it does and when to use it].
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return "my_custom_tool"

    @property
    def description(self) -> str:
        """Human-readable description for LLM."""
        return "Does something useful with [inputs]"

    def execute(self, param1: str, param2: int = 10) -> ToolResult:
        """
        Execute the tool.

        Args:
            param1: Description of first parameter
            param2: Description of second parameter (default: 10)

        Returns:
            ToolResult with success/failure and data
        """
        self.logger.info(f"Executing {self.name} with {param1}, {param2}")

        try:
            # 1. Validate inputs
            if not param1:
                return ToolResult(
                    success=False,
                    error="param1 cannot be empty"
                )

            # 2. Perform main logic
            result = self._do_work(param1, param2)

            # 3. Save state if needed
            self._save_state(result)

            # 4. Return success
            return ToolResult(
                success=True,
                data=result,
                message=f"Successfully processed {param1}"
            )

        except Exception as e:
            # 5. Handle errors gracefully
            self.logger.error(f"Error in {self.name}: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to process: {str(e)}"
            )

    def _do_work(self, param1: str, param2: int) -> Any:
        """Internal implementation."""
        # Your logic here
        return {"result": "data"}

    def _save_state(self, result: Any):
        """Save results to cache/disk if needed."""
        cache_file = Path(self.config.home_dir) / "my_tool_cache.json"
        # Save logic here
```

---

**End of Document**

For questions or contributions, see: https://github.com/SL-Mar/quantcoder-cli
