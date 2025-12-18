# Architecture Comparison: QuantCoder Gamma vs OpenCode

A comprehensive comparison of the architectural patterns, design decisions, and technical approaches used by **QuantCoder (Gamma Branch)** and **OpenCode**.

---

## Executive Summary

| Aspect | QuantCoder Gamma | OpenCode |
|--------|------------------|----------|
| **Language** | Python | Go |
| **Primary Purpose** | QuantConnect algo generation | General-purpose coding assistant |
| **UI Framework** | Rich + Click CLI | Bubble Tea TUI |
| **Architecture Pattern** | Multi-Agent Orchestration | Event-Driven MVU |
| **Storage** | SQLite (Learning DB) | SQLite (Sessions) |
| **LLM Integration** | Multi-provider + task-specific routing | Multi-provider with unified interface |
| **Tool System** | Custom tool classes | MCP Protocol + built-in tools |

---

## 1. Overall Architecture Philosophy

### QuantCoder Gamma: Domain-Specific Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER REQUEST                               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  COORDINATOR AGENT                              │
│  • Request analysis   • Task decomposition   • Plan creation    │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Universe   │  │   Alpha     │  │    Risk     │
│   Agent     │  │   Agent     │  │   Agent     │
└─────────────┘  └─────────────┘  └─────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MCP VALIDATION                                │
│  • QuantConnect API   • Backtesting   • Error fixing            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- **Specialized agents** for each code component (Universe, Alpha, Risk, Strategy)
- **Parallel execution** of independent agents for performance
- **Domain-focused**: Built specifically for QuantConnect algorithmic trading
- **Self-improving**: Learning database tracks errors and successful patterns

### OpenCode: General-Purpose Event-Driven TUI

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TUI (Bubble Tea)                             │
│  • Input handling   • Display   • Event processing              │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION MANAGER                              │
│  • Context management   • Message history   • Auto-compact      │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI AGENT LOOP                               │
│  • LLM Provider   • Tool execution   • Response streaming       │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TOOL SYSTEM                                │
│  • Bash   • File ops   • LSP   • MCP servers                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- **Single agent** with tool-calling capabilities
- **Model-View-Update (MVU)** pattern from Bubble Tea
- **General purpose**: Works with any codebase or language
- **Permission system**: User approves tool executions

---

## 2. Language & Technology Stack Comparison

| Component | QuantCoder Gamma | OpenCode |
|-----------|------------------|----------|
| **Primary Language** | Python 3.11+ | Go 1.21+ |
| **CLI Framework** | Click + Rich | Bubble Tea (TUI) |
| **Async Runtime** | asyncio | Go goroutines |
| **Database** | SQLite (autonomous learning) | SQLite (sessions, files) |
| **Config Format** | TOML | JSON (.opencode.json) |
| **Package Manager** | pip/poetry | Go modules |
| **Testing** | pytest | Go test |

### Implications

**Python (Gamma):**
- Faster prototyping and iteration
- Rich ecosystem of ML/data science libraries
- Native async/await for parallel agent execution
- Easier integration with LLM SDKs (all have Python SDKs)

**Go (OpenCode):**
- Superior runtime performance
- Single binary distribution
- Better concurrency primitives
- Memory safety without GC pauses affecting TUI

---

## 3. Agent Architecture

### QuantCoder Gamma: Multi-Agent Orchestration

```python
# Base agent pattern
class BaseAgent(ABC):
    def __init__(self, llm: LLMProvider, config: Any = None):
        self.llm = llm
        self.config = config

    @abstractmethod
    async def execute(self, **kwargs) -> AgentResult:
        pass

# Specialized agents
class UniverseAgent(BaseAgent):   # Stock screening
class AlphaAgent(BaseAgent):       # Signal generation
class RiskAgent(BaseAgent):        # Position sizing
class StrategyAgent(BaseAgent):    # Main algorithm
class CoordinatorAgent(BaseAgent): # Orchestration
```

**Agent Execution Flow:**
1. Coordinator analyzes request → creates execution plan
2. Independent agents run in parallel (Universe + Alpha)
3. Dependent agents wait for prerequisites (Risk needs Alpha)
4. Integration agent combines all files
5. MCP validation → error fixing loop

**LLM Routing by Task:**
- **Sonnet 4.5**: Coordinator, Risk (complex reasoning)
- **Devstral**: Code generation agents (specialized for code)
- **DeepSeek**: Alternative code generation

### OpenCode: Single Agent with Tools

```go
// Session orchestrates the AI loop
type Session struct {
    ID       string
    Messages []Message
    Provider Provider
    Tools    []Tool
}

// Agent loop pattern
func (s *Session) Prompt(input string) Response {
    // 1. Add user message
    // 2. Call LLM with tools
    // 3. Execute tool calls
    // 4. Loop until done
    // 5. Return response
}
```

**Tool Execution Flow:**
1. User input → LLM request with tool definitions
2. LLM returns tool calls
3. Permission check (dialog for approval)
4. Tool execution
5. Results fed back to LLM
6. Continue until no more tool calls

**LLM Provider Abstraction:**
- Single unified interface for all providers
- User selects model via Ctrl+O picker
- No task-specific routing (same model for all tasks)

---

## 4. Tool System Architecture

### QuantCoder Gamma: Custom Tool Classes

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: pass

# Domain-specific tools
class SearchArticlesTool(Tool):      # CrossRef search
class DownloadArticleTool(Tool):     # PDF download
class SummarizeArticleTool(Tool):    # LLM summarization
class GenerateCodeTool(Tool):        # Code generation
class ValidateCodeTool(Tool):        # QC validation
```

**Tool Categories:**
- **Article Tools**: Search, download, summarize research papers
- **Code Tools**: Generate, validate, refine QuantConnect code
- **File Tools**: Read, write, manage generated files

### OpenCode: MCP Protocol + Built-in Tools

```go
// Built-in tools
type BashTool struct{}        // Shell execution
type FileTool struct{}        // File operations
type SearchTool struct{}      // Code search
type LSPTool struct{}         // Language server

// MCP integration
type MCPServer struct {
    Name  string
    Tools []MCPTool
}
```

**Tool Categories:**
- **Built-in**: Bash, file operations, grep, diagnostics
- **LSP Integration**: Code intelligence from language servers
- **MCP Servers**: External tools via Model Context Protocol
- **Custom**: User-defined tools through MCP

### Key Differences

| Aspect | QuantCoder Gamma | OpenCode |
|--------|------------------|----------|
| **Tool Definition** | Python ABC classes | Go interfaces + MCP |
| **Extensibility** | Subclass Tool | MCP server protocol |
| **Permissions** | auto_approve config flag | Dialog-based approval |
| **Domain Focus** | Finance/trading specific | General-purpose |

---

## 5. LLM Provider Integration

### QuantCoder Gamma: Multi-Provider with Task Routing

```python
class LLMFactory:
    @staticmethod
    def create(provider: str, api_key: str, model: str = None):
        if provider == "anthropic":
            return AnthropicProvider(api_key, model)
        elif provider == "mistral":
            return MistralProvider(api_key, model)
        elif provider == "deepseek":
            return DeepSeekProvider(api_key, model)

    @staticmethod
    def get_recommended_for_task(task: str) -> str:
        recommendations = {
            "coding": "mistral",      # Devstral for code
            "reasoning": "anthropic",  # Sonnet for logic
            "risk": "anthropic",      # Complex analysis
        }
        return recommendations.get(task, "anthropic")
```

**Providers:**
- Anthropic (Claude)
- Mistral (Devstral)
- DeepSeek

### OpenCode: Unified Provider Interface

```go
type Provider interface {
    Chat(messages []Message) (Response, error)
    Stream(messages []Message) chan Response
    GetModel() string
}

// Supported providers
- OpenAI (GPT-4.1, GPT-4o, O1/O3)
- Anthropic (Claude 3.5-4)
- Google (Gemini 2.0-2.5)
- AWS Bedrock
- Groq
- Azure OpenAI
- OpenRouter
- Google VertexAI
- GitHub Copilot
```

**Key Difference:** OpenCode supports more providers but uses the same model for all tasks. QuantCoder routes different task types to specialized models.

---

## 6. State Management & Persistence

### QuantCoder Gamma: Learning Database

```python
class LearningDatabase:
    """Tracks generation history and errors for self-improvement."""

    def save_generation(self, strategy, errors, refinements, metrics):
        # Store for pattern learning

    def get_common_errors(self, limit=10):
        # Identify recurring issues

    def get_library_stats(self):
        # Success rates, Sharpe ratios, etc.
```

**Persistence:**
- Strategy generation history
- Error patterns and fixes
- Performance metrics (Sharpe, returns)
- Category/taxonomy of strategies

### OpenCode: Session-Based Storage

```go
type Storage struct {
    db *sql.DB
}

func (s *Storage) SaveSession(session Session) error
func (s *Storage) LoadSession(id string) (Session, error)
func (s *Storage) ListSessions() ([]Session, error)
```

**Persistence:**
- Conversation sessions
- Message history
- File change history
- No learning/improvement tracking

---

## 7. Execution Models

### QuantCoder Gamma: Parallel Agent Execution

```python
class ParallelExecutor:
    async def execute_agents_parallel(self, tasks: List[AgentTask]) -> List[Any]:
        """Execute multiple agents concurrently."""
        return await asyncio.gather(*[
            self._run_agent_async(task.agent, task.params)
            for task in tasks
        ])
```

**Execution Strategy:**
```
Request → Coordinator
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Universe Agent    Alpha Agent  (PARALLEL)
    ↓                   ↓
    └─────────┬─────────┘
              ↓
        Risk Agent           (SEQUENTIAL - needs Alpha)
              ↓
       Strategy Agent        (SEQUENTIAL - needs all)
              ↓
        MCP Validation
```

### OpenCode: Sequential Tool Execution

```go
func (a *Agent) Run(input string) {
    for {
        response := a.provider.Chat(messages)

        if !response.HasToolCalls() {
            break  // Done
        }

        for _, call := range response.ToolCalls {
            result := a.executeTool(call)  // One at a time
            messages = append(messages, result)
        }
    }
}
```

**Execution Strategy:**
```
User Input → LLM → Tool Call → Execute → Result → LLM → ...
                        ↓
                  (Sequential loop until complete)
```

---

## 8. User Interface Comparison

### QuantCoder Gamma: Rich CLI

```python
# Click-based CLI with Rich formatting
@click.command()
def interactive(config: Config):
    console.print(Panel.fit(
        "[bold cyan]QuantCoder v2.0[/bold cyan]\n"
        "AI-powered CLI for QuantConnect algorithms",
        title="Welcome"
    ))
    chat = InteractiveChat(config)
    chat.run()
```

**UI Features:**
- Markdown rendering in terminal
- Syntax highlighting for code
- Progress spinners
- Colored output
- Subcommand structure (search, download, generate)

### OpenCode: Full TUI (Terminal User Interface)

```go
// Bubble Tea model
type Model struct {
    input    textinput.Model
    viewport viewport.Model
    messages []Message
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        // Handle keyboard shortcuts
    }
}
```

**UI Features:**
- Full-screen terminal application
- Vim-like text editing
- Session switching (Ctrl+A)
- Model picker (Ctrl+O)
- Debug log viewer (Ctrl+L)
- External editor integration (Ctrl+E)

---

## 9. MCP (Model Context Protocol) Integration

### QuantCoder Gamma: Custom MCP Client for QuantConnect

```python
class QuantConnectMCPClient:
    """MCP client specifically for QuantConnect API."""

    async def validate_code(self, code: str, files: Dict) -> Dict:
        # Compile and validate with QC API

    async def backtest(self, code: str, start: str, end: str) -> Dict:
        # Run backtest on QC platform

    async def deploy_live(self, project_id: str, node_id: str) -> Dict:
        # Deploy to live trading
```

**MCP Usage:** Domain-specific integration with QuantConnect platform for validation, backtesting, and deployment.

### OpenCode: General MCP Server Support

```go
// MCP server configuration
type MCPConfig struct {
    Name    string
    Command string
    Args    []string
}

// Generic MCP tool invocation
func (m *MCPClient) CallTool(name string, args map[string]any) (any, error)
```

**MCP Usage:** Generic protocol for extending capabilities with any MCP-compatible server (file systems, databases, APIs).

---

## 10. Error Handling & Self-Improvement

### QuantCoder Gamma: Learning from Errors

```python
class ErrorLearner:
    """Learn from generation errors to improve over time."""

    def analyze_error(self, error: str, code: str) -> Fix:
        # Pattern match against known fixes

    def record_successful_fix(self, error: str, fix: str):
        # Store for future use

    def get_fix_suggestions(self, error: str) -> List[str]:
        # Retrieve relevant fixes from history
```

**Self-Improvement Loop:**
1. Generate code → Validation error
2. Store error pattern in learning DB
3. Attempt fix with LLM
4. If successful, store fix pattern
5. Future similar errors → retrieve proven fix

### OpenCode: Auto-Compact for Context Management

```go
// Context window management
func (s *Session) AutoCompact() {
    if s.TokenUsage > s.TokenLimit * 0.95 {
        // Summarize conversation
        summary := s.provider.Summarize(s.Messages)
        s.Messages = []Message{{Role: "system", Content: summary}}
    }
}
```

**No Learning:** OpenCode handles errors through the standard agent loop but doesn't build a learning database.

---

## 11. Deployment & Distribution

### QuantCoder Gamma

```toml
# pyproject.toml
[project]
name = "quantcoder"
requires-python = ">=3.11"

[project.scripts]
quantcoder = "quantcoder.cli:main"
```

**Distribution:**
- PyPI package
- `pip install quantcoder`
- Requires Python runtime

### OpenCode

```yaml
# Release artifacts
- opencode_linux_amd64
- opencode_darwin_amd64
- opencode_darwin_arm64
- opencode_windows_amd64.exe
```

**Distribution:**
- Single binary (no runtime needed)
- Homebrew: `brew install opencode`
- Direct download from GitHub releases

---

## 12. Summary: When to Use Each

### Use QuantCoder Gamma When:
- Building QuantConnect trading algorithms
- Need specialized multi-agent coordination
- Want domain-specific LLM routing
- Require self-improving error handling
- Working with financial research papers
- Building a strategy library systematically

### Use OpenCode When:
- General-purpose coding assistance
- Need polished TUI experience
- Working across multiple languages/frameworks
- Want single-binary deployment
- Need broad LLM provider support
- Prefer MCP extensibility model

---

## 13. Architectural Lessons & Best Practices

### From QuantCoder Gamma:
1. **Specialized agents outperform generalists** for domain-specific tasks
2. **Parallel execution** significantly speeds up multi-component generation
3. **Learning databases** enable continuous improvement
4. **Task-specific LLM routing** optimizes quality and cost

### From OpenCode:
1. **Unified provider interface** simplifies multi-LLM support
2. **Permission systems** build user trust
3. **Auto-compact** elegantly handles context limits
4. **MCP protocol** provides infinite extensibility
5. **TUI framework** (Bubble Tea) enables rich terminal UX

---

## Sources

- [OpenCode GitHub Repository](https://github.com/opencode-ai/opencode)
- [OpenCode Documentation](https://opencode.ai/docs/cli/)
- [freeCodeCamp - Integrate AI into Your Terminal Using OpenCode](https://www.freecodecamp.org/news/integrate-ai-into-your-terminal-using-opencode/)
- [DeepWiki - OpenCode Architecture](https://deepwiki.com/opencode-ai/opencode)
