# Architecture Adaptations: From QuantCoder to Research Assistant & Trading Operator

This document outlines how to adapt the QuantCoder Gamma multi-agent architecture for two new use cases:
1. **Research Assistant** - AI-powered research and analysis tool
2. **Trading Operator** - Automated trading operations system

---

## Source Architecture: QuantCoder Gamma

### Core Patterns to Reuse

```
┌─────────────────────────────────────────────────────────────────┐
│                   REUSABLE COMPONENTS                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Multi-Agent Orchestration (coordinator_agent.py)            │
│  2. Parallel Execution Framework (parallel_executor.py)         │
│  3. LLM Provider Abstraction (llm/providers.py)                 │
│  4. Tool System Base Classes (tools/base.py)                    │
│  5. Learning Database (autonomous/database.py)                  │
│  6. CLI Framework (cli.py with Click + Rich)                    │
│  7. Configuration System (config.py)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Research Assistant Architecture

### Vision
An AI-powered research assistant that can:
- Search and analyze academic papers, patents, and web sources
- Synthesize findings across multiple sources
- Generate reports, summaries, and literature reviews
- Track research threads and maintain context over time

### Agent Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER QUERY                                 │
│  "Find papers on transformer architectures for time series"    │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RESEARCH COORDINATOR                           │
│  • Parse research question                                      │
│  • Identify source types needed                                 │
│  • Plan search strategy                                         │
│  • Orchestrate specialized agents                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Search    │  │   Paper     │  │   Patent    │  │    Web      │
│   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │
│             │  │             │  │             │  │             │
│ • CrossRef  │  │ • ArXiv     │  │ • USPTO     │  │ • Google    │
│ • Semantic  │  │ • PDF parse │  │ • EPO       │  │ • News      │
│   Scholar   │  │ • Citations │  │ • WIPO      │  │ • Blogs     │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
        │                │                │              │
        └────────────────┴────────────────┴──────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SYNTHESIS AGENT                               │
│  • Cross-reference findings                                     │
│  • Identify themes and gaps                                     │
│  • Generate structured summary                                  │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   REPORT AGENT                                  │
│  • Format output (Markdown, PDF, LaTeX)                         │
│  • Create citations                                             │
│  • Generate bibliography                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Implementations

```python
# research_assistant/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional

@dataclass
class ResearchResult:
    """Result from a research agent."""
    success: bool
    sources: List[dict] = None
    summary: str = None
    error: Optional[str] = None
    metadata: dict = None

class BaseResearchAgent(ABC):
    """Base class for research agents."""

    def __init__(self, llm, config=None):
        self.llm = llm
        self.config = config

    @property
    @abstractmethod
    def agent_name(self) -> str:
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Type of sources this agent searches (papers, patents, web)."""
        pass

    @abstractmethod
    async def search(self, query: str, **kwargs) -> ResearchResult:
        """Search for sources matching the query."""
        pass

    @abstractmethod
    async def analyze(self, source: dict) -> dict:
        """Analyze a single source and extract key information."""
        pass
```

```python
# research_assistant/agents/search_agent.py
class SearchAgent(BaseResearchAgent):
    """Agent for academic paper search across multiple databases."""

    agent_name = "SearchAgent"
    source_type = "academic"

    def __init__(self, llm, config=None):
        super().__init__(llm, config)
        self.databases = {
            "crossref": CrossRefClient(),
            "semantic_scholar": SemanticScholarClient(),
            "arxiv": ArxivClient(),
        }

    async def search(self, query: str, databases: List[str] = None,
                     max_results: int = 20) -> ResearchResult:
        """Search multiple academic databases in parallel."""
        dbs = databases or list(self.databases.keys())

        # Parallel search across databases
        tasks = [
            self._search_database(db, query, max_results)
            for db in dbs
        ]
        results = await asyncio.gather(*tasks)

        # Merge and deduplicate
        all_sources = self._merge_results(results)

        return ResearchResult(
            success=True,
            sources=all_sources,
            summary=f"Found {len(all_sources)} papers across {len(dbs)} databases"
        )
```

```python
# research_assistant/agents/synthesis_agent.py
class SynthesisAgent(BaseResearchAgent):
    """Agent for synthesizing findings across multiple sources."""

    agent_name = "SynthesisAgent"
    source_type = "synthesis"

    async def synthesize(self, sources: List[dict],
                         research_question: str) -> ResearchResult:
        """Synthesize findings from multiple sources."""

        # Group sources by theme
        themes = await self._identify_themes(sources)

        # Generate synthesis for each theme
        synthesis_prompt = f"""
        Research Question: {research_question}

        Sources: {json.dumps(sources, indent=2)}

        Themes Identified: {themes}

        Provide a comprehensive synthesis that:
        1. Summarizes key findings across sources
        2. Identifies areas of consensus and disagreement
        3. Highlights research gaps
        4. Suggests future research directions
        """

        synthesis = await self.llm.chat(synthesis_prompt)

        return ResearchResult(
            success=True,
            summary=synthesis,
            metadata={"themes": themes, "source_count": len(sources)}
        )
```

### Tools for Research Assistant

```python
# research_assistant/tools/
class SearchPapersTool(Tool):
    """Search academic papers across databases."""
    name = "search_papers"

class DownloadPDFTool(Tool):
    """Download and parse PDF papers."""
    name = "download_pdf"

class ExtractCitationsTool(Tool):
    """Extract and format citations from papers."""
    name = "extract_citations"

class SummarizePaperTool(Tool):
    """Generate LLM-powered paper summaries."""
    name = "summarize_paper"

class SearchPatentsTool(Tool):
    """Search patent databases."""
    name = "search_patents"

class WebSearchTool(Tool):
    """Search web sources with filtering."""
    name = "web_search"

class GenerateReportTool(Tool):
    """Generate formatted research reports."""
    name = "generate_report"

class ManageBibliographyTool(Tool):
    """Manage bibliography in various formats."""
    name = "manage_bibliography"
```

### CLI Commands

```python
@main.group()
def research():
    """Research assistant commands."""
    pass

@research.command()
@click.argument('query')
@click.option('--sources', default='all', help='Sources to search')
@click.option('--max-results', default=20, help='Maximum results per source')
def search(query, sources, max_results):
    """Search for research materials."""
    pass

@research.command()
@click.argument('topic')
@click.option('--depth', default='standard', help='Research depth')
def investigate(topic, depth):
    """Deep investigation of a research topic."""
    pass

@research.command()
@click.argument('paper_ids', nargs=-1)
@click.option('--format', default='markdown', help='Output format')
def synthesize(paper_ids, format):
    """Synthesize findings from multiple papers."""
    pass

@research.command()
@click.option('--format', default='markdown', help='Report format')
def report(format):
    """Generate research report from current session."""
    pass
```

---

## 2. Trading Operator Architecture

### Vision
An automated trading operations system that can:
- Monitor portfolio positions and P&L in real-time
- Execute trading signals from various sources
- Manage risk and position sizing automatically
- Generate reports and alerts
- Interface with multiple brokers

### Agent Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                   TRADING SIGNALS                               │
│  • Strategy signals   • Manual orders   • Alerts                │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 OPERATIONS COORDINATOR                          │
│  • Validate signals                                             │
│  • Check risk limits                                            │
│  • Route to appropriate agents                                  │
│  • Log all decisions                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┬──────────────────┐
    ▼                    ▼                    ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Position   │  │    Risk      │  │  Execution   │  │  Reporting   │
│   Agent      │  │    Agent     │  │    Agent     │  │    Agent     │
│              │  │              │  │              │  │              │
│ • Track P&L  │  │ • Limits     │  │ • Order mgmt │  │ • Daily P&L  │
│ • Holdings   │  │ • Drawdown   │  │ • Fills      │  │ • Positions  │
│ • NAV        │  │ • Exposure   │  │ • Slippage   │  │ • Alerts     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
        │                │                  │                │
        └────────────────┴──────────────────┴────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BROKER ADAPTERS                              │
│  • Interactive Brokers   • Alpaca   • TD Ameritrade             │
│  • QuantConnect          • Binance  • Custom API                │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Implementations

```python
# trading_operator/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional
from enum import Enum

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float

@dataclass
class OperationResult:
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    data: Any = None

class BaseOperatorAgent(ABC):
    """Base class for trading operator agents."""

    def __init__(self, broker, config=None):
        self.broker = broker
        self.config = config

    @property
    @abstractmethod
    def agent_name(self) -> str:
        pass
```

```python
# trading_operator/agents/position_agent.py
class PositionAgent(BaseOperatorAgent):
    """Agent for tracking positions and P&L."""

    agent_name = "PositionAgent"

    async def get_positions(self) -> List[Position]:
        """Get current portfolio positions."""
        raw_positions = await self.broker.get_positions()
        return [self._to_position(p) for p in raw_positions]

    async def get_portfolio_value(self) -> dict:
        """Get total portfolio value and breakdown."""
        positions = await self.get_positions()

        return {
            "total_value": sum(p.quantity * p.current_price for p in positions),
            "total_pnl": sum(p.unrealized_pnl for p in positions),
            "positions": len(positions),
            "long_exposure": sum(
                p.quantity * p.current_price for p in positions if p.quantity > 0
            ),
            "short_exposure": abs(sum(
                p.quantity * p.current_price for p in positions if p.quantity < 0
            )),
        }
```

```python
# trading_operator/agents/risk_agent.py
class RiskAgent(BaseOperatorAgent):
    """Agent for risk management and position sizing."""

    agent_name = "RiskAgent"

    def __init__(self, broker, config=None):
        super().__init__(broker, config)
        self.limits = config.risk_limits if config else self._default_limits()

    async def check_order(self, order: Order) -> tuple[bool, str]:
        """Check if order passes risk limits."""
        portfolio = await self.broker.get_portfolio()

        # Check position concentration
        if not self._check_concentration(order, portfolio):
            return False, f"Order exceeds position concentration limit"

        # Check total exposure
        if not self._check_exposure(order, portfolio):
            return False, f"Order exceeds total exposure limit"

        # Check drawdown
        if not self._check_drawdown(portfolio):
            return False, f"Portfolio drawdown exceeds limit"

        return True, "Order passes all risk checks"

    async def calculate_position_size(self, symbol: str,
                                       signal_strength: float = 1.0) -> float:
        """Calculate optimal position size based on risk parameters."""
        portfolio = await self.broker.get_portfolio()
        volatility = await self._get_volatility(symbol)

        # Risk-based position sizing
        risk_per_trade = self.limits.get("risk_per_trade", 0.02)
        portfolio_value = portfolio["total_value"]

        dollar_risk = portfolio_value * risk_per_trade
        position_size = dollar_risk / (volatility * signal_strength)

        # Apply limits
        max_position = portfolio_value * self.limits.get("max_position_pct", 0.10)
        return min(position_size, max_position)
```

```python
# trading_operator/agents/execution_agent.py
class ExecutionAgent(BaseOperatorAgent):
    """Agent for order execution and management."""

    agent_name = "ExecutionAgent"

    async def execute_order(self, order: Order) -> OperationResult:
        """Execute a trading order."""
        # Pre-execution checks
        risk_ok, risk_msg = await self.risk_agent.check_order(order)
        if not risk_ok:
            return OperationResult(success=False, message=risk_msg)

        # Execute with broker
        try:
            order_id = await self.broker.submit_order(order)
            fill = await self._wait_for_fill(order_id, timeout=60)

            return OperationResult(
                success=True,
                order_id=order_id,
                message=f"Order filled: {fill}",
                data=fill
            )
        except Exception as e:
            return OperationResult(success=False, message=str(e))
```

### Broker Adapters

```python
# trading_operator/brokers/base.py
class BaseBroker(ABC):
    """Abstract base class for broker adapters."""

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def get_positions(self) -> List[dict]:
        pass

    @abstractmethod
    async def get_portfolio(self) -> dict:
        pass

    @abstractmethod
    async def submit_order(self, order: Order) -> str:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

# Implementations for different brokers
class InteractiveBrokersBroker(BaseBroker): pass
class AlpacaBroker(BaseBroker): pass
class QuantConnectBroker(BaseBroker): pass
class BinanceBroker(BaseBroker): pass
```

### CLI Commands

```python
@main.group()
def operator():
    """Trading operator commands."""
    pass

@operator.command()
def status():
    """Show current portfolio status."""
    pass

@operator.command()
@click.argument('symbol')
@click.argument('side', type=click.Choice(['buy', 'sell']))
@click.argument('quantity', type=float)
def order(symbol, side, quantity):
    """Place a trading order."""
    pass

@operator.command()
def positions():
    """List current positions."""
    pass

@operator.command()
def pnl():
    """Show P&L summary."""
    pass

@operator.group()
def risk():
    """Risk management commands."""
    pass
```

---

## 3. Shared Components

### Project Structure Template

```
app_name/
├── app_name/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── chat.py             # Interactive chat mode
│   │
│   ├── agents/             # Multi-agent system
│   │   ├── __init__.py
│   │   ├── base.py         # Base agent class
│   │   ├── coordinator.py  # Main orchestrator
│   │   └── [specialized_agents].py
│   │
│   ├── tools/              # Tool implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Base tool class
│   │   └── [domain_tools].py
│   │
│   ├── execution/          # Parallel execution
│   │   ├── __init__.py
│   │   └── parallel_executor.py
│   │
│   ├── llm/                # LLM providers
│   │   ├── __init__.py
│   │   └── providers.py
│   │
│   └── autonomous/         # Self-improving mode
│       ├── __init__.py
│       ├── database.py
│       └── learner.py
│
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 4. Summary Comparison

| Component | QuantCoder Gamma | Research Assistant | Trading Operator |
|-----------|------------------|-------------------|------------------|
| **Coordinator** | Strategy planning | Research planning | Trade orchestration |
| **Parallel Agents** | Universe, Alpha, Risk | Search, Paper, Patent, Web | Position, Risk, Execution |
| **MCP Integration** | QuantConnect API | Paper databases | Broker APIs |
| **Learning DB** | Strategy errors | Research patterns | Trading patterns |
| **Output** | QC algorithms | Research reports | Trade logs, P&L |

The gamma architecture provides a solid foundation that can be adapted for any domain requiring:
- Multi-agent orchestration
- Parallel task execution
- LLM-powered analysis
- Domain-specific tool integration
- Self-improving capabilities
