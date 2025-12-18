# Architecture Comparison: Mistral Vibe CLI vs QuantCoder Gamma vs OpenCode

A comprehensive comparison of the architectural patterns, design decisions, and technical approaches used by three modern AI coding assistants for the terminal.

> **Note:** QuantCoder Gamma's CLI was explicitly **"inspired by Mistral Vibe CLI"** (see `quantcoder/cli.py:1`)

---

## Executive Summary

| Aspect | Mistral Vibe CLI | QuantCoder Gamma | OpenCode |
|--------|------------------|------------------|----------|
| **Language** | Python 3.12+ | Python 3.11+ | Go 1.21+ |
| **Primary Purpose** | General coding assistant | QuantConnect algo generation | General coding assistant |
| **UI Framework** | Rich CLI (interactive) | Rich + Click CLI | Bubble Tea TUI |
| **Architecture** | Single Agent + Tools | Multi-Agent Orchestration | Event-Driven MVU |
| **Default LLM** | Devstral (Mistral) | Multi-provider routing | User-selected |
| **Config Format** | TOML | TOML | JSON |
| **Tool System** | Built-in + MCP | Custom classes + MCP | Built-in + MCP |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

---

## 1. Overall Architecture Philosophy

### Mistral Vibe CLI: Minimal Single-Agent Design

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER INPUT                                 │
│  • Natural language   • @file refs   • !shell commands          │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PROJECT CONTEXT                                │
│  • File structure scan   • Git status   • Smart references      │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT LOOP                                   │
│  • Task decomposition   • Tool selection   • Execution          │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL SYSTEM                                  │
│  • read_file   • write_file   • bash   • grep   • todo          │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PERMISSION CHECK                                │
│  • always   • ask   • disabled                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- **Minimal design**: Focused, lean codebase
- **Project-aware**: Auto-scans file structure and Git status
- **Devstral-optimized**: Built for Mistral's code models (123B parameter)
- **Three-tier permissions**: Configurable tool approval levels

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
- **Permission system**: Dialog-based tool approval

---

## 2. Language & Technology Stack Comparison

| Component | Mistral Vibe CLI | QuantCoder Gamma | OpenCode |
|-----------|------------------|------------------|----------|
| **Primary Language** | Python 3.12+ | Python 3.11+ | Go 1.21+ |
| **CLI Framework** | Rich + custom | Click + Rich | Bubble Tea (TUI) |
| **Async Runtime** | asyncio | asyncio | Go goroutines |
| **Database** | None (stateless) | SQLite (learning) | SQLite (sessions) |
| **Config Format** | TOML | TOML | JSON |
| **Package Manager** | uv (recommended) | pip/poetry | Go modules |
| **Installation** | pip/uv/script | pip | Single binary |

### Implications

**Python (Vibe & Gamma):**
- Faster prototyping and iteration
- Rich ecosystem of ML/data science libraries
- Native async/await for concurrent operations
- Easier integration with LLM SDKs

**Go (OpenCode):**
- Superior runtime performance
- Single binary distribution
- Better concurrency primitives
- Memory safety without GC pauses affecting TUI

---

## 3. Project Structure Comparison

### Mistral Vibe CLI

```
mistral-vibe/
├── vibe/              # Main package
├── tests/             # Test suite
├── scripts/           # Utility scripts
└── .vibe/             # Configuration directory
    ├── config.toml    # Main configuration
    ├── .env           # API credentials
    ├── agents/        # Custom agent configs
    ├── prompts/       # System prompts
    └── logs/          # Session logs
```

### QuantCoder Gamma

```
quantcoder/
├── quantcoder/
│   ├── agents/        # Multi-agent system
│   │   ├── base.py
│   │   ├── coordinator_agent.py
│   │   ├── universe_agent.py
│   │   ├── alpha_agent.py
│   │   └── risk_agent.py
│   ├── autonomous/    # Self-improving mode
│   ├── library/       # Strategy library builder
│   ├── tools/         # Tool implementations
│   ├── llm/           # LLM providers
│   ├── mcp/           # QuantConnect MCP
│   └── cli.py         # Main entry point
├── tests/
└── docs/
```

### OpenCode

```
opencode/
├── cmd/              # CLI entry points
├── internal/         # Core application logic
├── scripts/          # Utility scripts
├── main.go           # Application entry point
├── go.mod            # Dependencies
└── .opencode.json    # Configuration
```

---

## 4. Agent Architecture Comparison

### Mistral Vibe: Single Agent with Tool Loop

```python
# Conceptual agent loop
class VibeAgent:
    def run(self, prompt: str):
        context = self.scan_project()  # File structure, git status

        while True:
            response = self.llm.chat(prompt, context, tools)

            if not response.tool_calls:
                return response.text

            for call in response.tool_calls:
                if self.check_permission(call.tool):
                    result = self.execute_tool(call)
                    context.add(result)
```

**Tool System:**
- `read_file`, `write_file`, `search_replace` - File operations
- `bash` - Stateful terminal execution
- `grep` - Code search (ripgrep support)
- `todo` - Task tracking

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

### OpenCode: Single Agent with Tools (Go)

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

---

## 5. Tool System Architecture

### Mistral Vibe CLI: Pattern-Based Permissions

```toml
# ~/.vibe/config.toml
[tools]
# Permission levels: always, ask, disabled

[tools.permissions]
read_file = "always"      # Auto-execute
write_file = "ask"        # Prompt user
bash = "ask"              # Prompt user

[tools.patterns]
# Glob/regex filtering for fine-grained control
allow = ["*.py", "*.js"]
deny = ["*.env", "secrets/*"]
```

**Unique Features:**
- Three-tier permission model (always/ask/disabled)
- Pattern-based tool filtering with glob/regex
- Stateful bash terminal (maintains context)
- Project-aware context injection

### QuantCoder Gamma: Domain-Specific Tools

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: pass

# Domain-specific tools
class SearchArticlesTool(Tool):      # CrossRef search
class DownloadArticleTool(Tool):     # PDF download
class SummarizeArticleTool(Tool):    # LLM summarization
class GenerateCodeTool(Tool):        # Code generation
class ValidateCodeTool(Tool):        # QC validation
```

### OpenCode: MCP Protocol + Built-in

```go
// Built-in tools
type BashTool struct{}
type FileTool struct{}
type SearchTool struct{}
type LSPTool struct{}

// MCP server integration
type MCPConfig struct {
    Name    string
    Command string
    Args    []string
}
```

### Tool Comparison Table

| Tool Type | Mistral Vibe | QuantCoder Gamma | OpenCode |
|-----------|--------------|------------------|----------|
| **File Read** | `read_file` | `ReadFileTool` | `FileTool` |
| **File Write** | `write_file` | `WriteFileTool` | `FileTool` |
| **Search/Replace** | `search_replace` | Edit tools | `FileTool` |
| **Shell** | `bash` (stateful) | `BashTool` | `BashTool` |
| **Code Search** | `grep` (ripgrep) | Grep tools | `SearchTool` |
| **Task Tracking** | `todo` | TodoWrite | None |
| **LSP** | None | None | `LSPTool` |
| **Domain-Specific** | None | Article/QC tools | None |

---

## 6. LLM Provider Integration

### Mistral Vibe: Devstral-First

```toml
# Default optimized for Devstral
[model]
provider = "mistral"
model = "devstral-small-2501"  # or devstral-2-123b

# Also supports
# provider = "anthropic"
# provider = "openai"
```

**Devstral Models:**
- **Devstral 2** (123B): 72.2% SWE-bench, 256K context, 4x H100 required
- **Devstral Small 2**: Single GPU, runs on RTX cards
- **Devstral Small**: CPU-only capable

### QuantCoder Gamma: Task-Specific Routing

```python
class LLMFactory:
    @staticmethod
    def get_recommended_for_task(task: str) -> str:
        recommendations = {
            "coding": "mistral",      # Devstral for code
            "reasoning": "anthropic",  # Sonnet for logic
            "risk": "anthropic",      # Complex analysis
        }
        return recommendations.get(task, "anthropic")
```

**Routing Strategy:**
- **Sonnet 4.5**: Coordinator, Risk (complex reasoning)
- **Devstral**: Code generation agents
- **DeepSeek**: Alternative code generation

### OpenCode: Provider Agnostic

```go
// Supported providers (10+)
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

---

## 7. Configuration Systems

### Mistral Vibe CLI

```toml
# ~/.vibe/config.toml

[model]
provider = "mistral"
model = "devstral-small-2501"
temperature = 0.7

[tools.permissions]
read_file = "always"
write_file = "ask"
bash = "ask"

[mcp.servers.filesystem]
transport = "stdio"
command = "npx"
args = ["-y", "@anthropic/mcp-filesystem"]
```

**Unique Features:**
- Custom agents in `~/.vibe/agents/`
- Custom prompts in `~/.vibe/prompts/`
- Project-level overrides in `./.vibe/config.toml`
- `VIBE_HOME` environment variable for custom paths

### QuantCoder Gamma

```toml
# config.toml

[model]
provider = "anthropic"
model = "claude-sonnet-4-5-20250929"
temperature = 0.7
max_tokens = 4000

[ui]
theme = "monokai"
auto_approve = false
show_token_usage = true

[tools]
downloads_dir = "~/.quantcoder/downloads"
generated_code_dir = "~/.quantcoder/generated"
enabled_tools = ["*"]
```

### OpenCode

```json
// .opencode.json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-20250929",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-filesystem"]
    }
  }
}
```

---

## 8. User Interface Features

| Feature | Mistral Vibe | QuantCoder Gamma | OpenCode |
|---------|--------------|------------------|----------|
| **UI Type** | Interactive CLI | Rich CLI | Full TUI |
| **Multi-line Input** | `Ctrl+J` / `Shift+Enter` | Standard | Native |
| **File Autocomplete** | `@` symbol | None | None |
| **Shell Access** | `!` prefix | Subcommand | Tool call |
| **Auto-approve Toggle** | `Shift+Tab` | Config flag | Dialog |
| **Session Switching** | None | None | `Ctrl+A` |
| **Model Picker** | None | None | `Ctrl+O` |
| **Vim Editing** | None | None | Built-in |
| **External Editor** | None | None | `Ctrl+E` |

### Mistral Vibe: Smart References

```bash
# File autocomplete
vibe> Explain @src/main.py

# Direct shell execution
vibe> !git status

# Multi-line input
vibe> [Ctrl+J for newline]
```

### QuantCoder Gamma: Subcommand Structure

```bash
# Search articles
quantcoder search "momentum trading"

# Generate code
quantcoder generate 1

# Autonomous mode
quantcoder auto start --query "momentum" --max-iterations 50

# Library builder
quantcoder library build --comprehensive
```

### OpenCode: Full TUI Experience

```
┌──────────────────────────────────────────┐
│  OpenCode v1.0                    Ctrl+? │
├──────────────────────────────────────────┤
│                                          │
│  [Conversation history viewport]         │
│                                          │
├──────────────────────────────────────────┤
│  > Your prompt here...                   │
└──────────────────────────────────────────┘
```

---

## 9. MCP Integration Comparison

### Mistral Vibe: Three Transport Types

```toml
[mcp.servers.github]
transport = "http"
url = "https://api.github.com/mcp"
headers = { Authorization = "Bearer ${GITHUB_TOKEN}" }

[mcp.servers.local]
transport = "stdio"
command = "python"
args = ["-m", "my_mcp_server"]

[mcp.servers.streaming]
transport = "streamable-http"
url = "http://localhost:8080/mcp"
```

### QuantCoder Gamma: Domain-Specific MCP

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

### OpenCode: Generic MCP Support

```go
// MCP server configuration
type MCPConfig struct {
    Name    string
    Command string
    Args    []string
}
```

---

## 10. Unique Features by Platform

### Mistral Vibe CLI Unique Features

1. **Project-Aware Context**: Auto-scans file structure and Git status
2. **Stateful Bash**: Terminal maintains execution context across commands
3. **Pattern-Based Tool Filtering**: Glob/regex for fine-grained permissions
4. **Custom Agents**: Project-specific agent configurations
5. **Custom Prompts**: Override system instructions per project
6. **Devstral Optimization**: Built for Mistral's code models
7. **Zed IDE Integration**: Available as Zed extension

### QuantCoder Gamma Unique Features

1. **Multi-Agent Orchestration**: Specialized agents for different tasks
2. **Parallel Agent Execution**: Independent agents run concurrently
3. **Learning Database**: Tracks errors and fixes for improvement
4. **Task-Specific LLM Routing**: Different models for different tasks
5. **Autonomous Mode**: Self-improving strategy generation
6. **Library Builder**: Systematic strategy library creation
7. **QuantConnect MCP**: Validation, backtesting, deployment integration

### OpenCode Unique Features

1. **Full TUI**: Rich terminal user interface with Bubble Tea
2. **Auto-Compact**: Automatic context summarization at 95% capacity
3. **LSP Integration**: Language server protocol for code intelligence
4. **10+ LLM Providers**: Broadest provider support
5. **Session Management**: Switch between conversations
6. **Vim-like Editor**: Built-in text editing
7. **Single Binary**: No runtime dependencies

---

## 11. Execution Model Comparison

```
MISTRAL VIBE:
User Input → Context Scan → LLM → Tool Call → Permission Check → Execute → Loop
                ↓
        (Project-aware context injection)

QUANTCODER GAMMA:
Request → Coordinator → [Parallel Agents] → Integration → MCP Validation → Refinement
                              ↓
                    (Task-specific LLM routing)

OPENCODE:
User Input → Session → LLM → Tool Call → Dialog Approval → Execute → Auto-Compact → Loop
                                              ↓
                                      (Context management)
```

---

## 12. Performance & Resource Requirements

| Aspect | Mistral Vibe | QuantCoder Gamma | OpenCode |
|--------|--------------|------------------|----------|
| **Startup Time** | ~1s (Python) | ~1s (Python) | <100ms (Go binary) |
| **Memory Usage** | Moderate | Higher (multi-agent) | Low |
| **LLM Model** | Devstral (123B/Small) | Multi-provider | User choice |
| **GPU Required** | Optional (Small model) | API-based | API-based |
| **Local Model Support** | Yes (Devstral Small) | Via providers | Via providers |

### Devstral Hardware Requirements

| Model | Requirements |
|-------|--------------|
| Devstral 2 (123B) | 4x H100 GPUs minimum |
| Devstral Small 2 | Single GPU (RTX capable) |
| Devstral Small | CPU-only supported |

---

## 13. Summary: When to Use Each

### Use Mistral Vibe CLI When:
- Want minimal, focused coding assistant
- Using Mistral's Devstral models
- Need project-aware context automatically
- Want fine-grained tool permission control
- Running local models on consumer hardware
- Using Zed IDE

### Use QuantCoder Gamma When:
- Building QuantConnect trading algorithms
- Need specialized multi-agent coordination
- Want domain-specific LLM routing
- Require self-improving error handling
- Working with financial research papers
- Building a strategy library systematically

### Use OpenCode When:
- Need polished full-screen TUI experience
- Working across multiple languages/frameworks
- Want single-binary deployment
- Need broadest LLM provider support
- Prefer LSP-powered code intelligence
- Want session management and switching

---

## 14. Architectural Lessons

### From Mistral Vibe CLI:
1. **Minimal design** can be more effective than feature-bloat
2. **Project-aware context** improves response relevance
3. **Stateful tools** (bash) enable complex workflows
4. **Pattern-based permissions** provide security with flexibility
5. **Custom agents/prompts** enable project-specific customization

### From QuantCoder Gamma:
1. **Specialized agents outperform generalists** for domain-specific tasks
2. **Parallel execution** significantly speeds up multi-component generation
3. **Learning databases** enable continuous improvement
4. **Task-specific LLM routing** optimizes quality and cost
5. **MCP for validation** closes the feedback loop

### From OpenCode:
1. **Unified provider interface** simplifies multi-LLM support
2. **Permission dialogs** build user trust
3. **Auto-compact** elegantly handles context limits
4. **MCP protocol** provides infinite extensibility
5. **TUI framework** (Bubble Tea) enables rich terminal UX

---

## 15. Lineage & Inspiration

```
Mistral Vibe CLI (Dec 2025)
        │
        ├──→ QuantCoder Gamma (inspired by)
        │         │
        │         └── Multi-agent extension
        │             Domain specialization
        │             Learning database
        │
        └──→ OpenCode (parallel evolution)
                  │
                  └── Go rewrite
                      Full TUI
                      Broader provider support
```

**QuantCoder Gamma explicitly acknowledges Mistral Vibe CLI as inspiration** in its source code, while extending the concept with:
- Multi-agent orchestration instead of single agent
- Domain-specific tools for QuantConnect
- Learning database for self-improvement
- Task-specific LLM routing

---

## Sources

- [Mistral Vibe CLI GitHub](https://github.com/mistralai/mistral-vibe)
- [Mistral AI - Devstral 2 Announcement](https://mistral.ai/news/devstral-2-vibe-cli)
- [OpenCode GitHub Repository](https://github.com/opencode-ai/opencode)
- [OpenCode Documentation](https://opencode.ai/docs/cli/)
- [TechCrunch - Mistral Vibe Coding](https://techcrunch.com/2025/12/09/mistral-ai-surfs-vibe-coding-tailwinds-with-new-coding-models/)
- [MarkTechPost - Devstral 2 and Vibe CLI](https://www.marktechpost.com/2025/12/09/mistral-ai-ships-devstral-2-coding-models-and-mistral-vibe-cli-for-agentic-terminal-native-development/)
- [Analytics Vidhya - Mistral DevStral 2 Guide](https://www.analyticsvidhya.com/blog/2025/12/mistral-devstral-2-and-vibe-cli/)
