# QuantCoder v3.0 Architecture: Multi-Agent System for QuantConnect

> Claude Code equivalent for QuantConnect algorithm generation

---

## 🎯 Vision

Create a **multi-agentic system** that:
- Generates QuantConnect algorithms with **multiple files** (Main, Universe, Alpha, Risk)
- Uses **specialized agents** for different aspects of the strategy
- Executes agents in **parallel** for maximum performance
- Communicates with **QuantConnect via MCP** for real-time validation
- Supports **multiple LLMs** (Devstral, OSS-20B, Sonnet 4.5)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      User Request                                   │
│  "Generate a momentum strategy with custom universe selection"     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Coordinator Agent                                 │
│  • Analyzes request                                                 │
│  • Decomposes into sub-tasks                                        │
│  • Plans agent execution order                                      │
│  • Spawns specialized agents                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┬──────────────┐
                ▼                         ▼              ▼
    ┌───────────────────┐    ┌───────────────────┐  ┌──────────────────┐
    │  Strategy Agent   │    │  Universe Agent   │  │   Alpha Agent    │
    │                   │    │                   │  │                  │
    │ • Overall logic   │    │ • Stock filters   │  │ • Signal gen     │
    │ • Risk mgmt       │    │ • Screening       │  │ • Indicators     │
    │ • Main.py         │    │ • Universe.py     │  │ • Alpha.py       │
    └─────────┬─────────┘    └─────────┬─────────┘  └────────┬─────────┘
              │                        │                      │
              │        ┌───────────────┴───────────┐         │
              │        ▼                           ▼         │
              │  ┌──────────────────┐    ┌──────────────────┐│
              │  │   Risk Agent     │    │  Portfolio Agent ││
              │  │                  │    │                  ││
              │  │ • Position size  │    │ • Rebalancing    ││
              │  │ • Stop loss      │    │ • Execution      ││
              │  │ • Risk.py        │    │ • Portfolio.py   ││
              │  └────────┬─────────┘    └────────┬─────────┘│
              │           │                       │          │
              └───────────┴───────────────────────┴──────────┘
                                    │
                                    ▼
                ┌────────────────────────────────────────────┐
                │         Integration Agent                  │
                │  • Combines all files                      │
                │  • Ensures consistency                     │
                │  • Resolves dependencies                   │
                └─────────────────┬──────────────────────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────────────┐
                │      MCP Client (QuantConnect)             │
                │  • Validates code against QC API           │
                │  • Runs backtest                           │
                │  • Returns metrics & errors                │
                └─────────────────┬──────────────────────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────────────┐
                │    Refinement Loop (if needed)             │
                │  • Coordinator reviews results             │
                │  • Spawns agents to fix issues             │
                │  • Validates again                         │
                └─────────────────┬──────────────────────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────────────┐
                │         Deliverables                       │
                │  ✓ Main.py                                 │
                │  ✓ Universe.py                             │
                │  ✓ Alpha.py                                │
                │  ✓ Risk.py                                 │
                │  ✓ Portfolio.py                            │
                │  ✓ Validation report                       │
                │  ✓ Backtest results                        │
                └────────────────────────────────────────────┘
```

---

## 🤖 Agent Specifications

### **1. Coordinator Agent** (Main Orchestrator)

**Role:** Strategic planning and orchestration

**Responsibilities:**
- Parse user request
- Identify required components (universe, alpha, risk, etc.)
- Determine execution order
- Spawn specialized agents in parallel where possible
- Integrate results
- Validate final output

**LLM:** Sonnet 4.5 (best reasoning)

**Example:**
```python
User: "Create momentum strategy with S&P 500 universe"

Coordinator thinks:
  ✓ Need Universe Agent (S&P 500 filtering)
  ✓ Need Alpha Agent (momentum signals)
  ✓ Need Risk Agent (position sizing, stops)
  ✓ Need Strategy Agent (main algorithm)

  Execution plan:
    1. Universe Agent + Alpha Agent (parallel)
    2. Wait for both
    3. Risk Agent (uses Alpha output)
    4. Strategy Agent (integrates all)
    5. Validation via MCP
```

---

### **2. Universe Agent** (Stock Selection)

**Role:** Generate stock screening logic

**Responsibilities:**
- Define universe selection criteria
- Implement filters (liquidity, market cap, sector)
- Create `Universe.py` module
- Ensure efficient universe updates

**LLM:** Devstral (code-specialized)

**Output:** `Universe.py`
```python
class CustomUniverseSelectionModel:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def SelectCoarse(self, algorithm, coarse):
        # Filter: Top 500 by dollar volume
        sorted_by_dollar_volume = sorted(
            coarse,
            key=lambda x: x.DollarVolume,
            reverse=True
        )
        return [x.Symbol for x in sorted_by_dollar_volume[:500]]

    def SelectFine(self, algorithm, fine):
        # Filter: Market cap > $1B, no financials
        return [
            x.Symbol for x in fine
            if x.MarketCap > 1e9
            and x.AssetClassification.MorningstarSectorCode != 103
        ]
```

---

### **3. Alpha Agent** (Signal Generation)

**Role:** Create trading signals

**Responsibilities:**
- Implement indicators (momentum, mean reversion, etc.)
- Define entry/exit logic
- Create `Alpha.py` module
- Optimize for performance

**LLM:** Devstral or OSS-20B

**Output:** `Alpha.py`
```python
class MomentumAlphaModel:
    def __init__(self, algorithm, lookback=20):
        self.algorithm = algorithm
        self.lookback = lookback
        self.momentum = {}

    def Update(self, algorithm, data):
        insights = []

        for symbol in algorithm.ActiveSecurities.Keys:
            if not data.ContainsKey(symbol):
                continue

            # Calculate momentum
            history = algorithm.History(symbol, self.lookback, Resolution.Daily)
            if len(history) < self.lookback:
                continue

            momentum = (history['close'][-1] / history['close'][0]) - 1

            # Generate signal
            if momentum > 0.05:  # 5% gain
                insights.append(
                    Insight.Price(
                        symbol,
                        timedelta(days=1),
                        InsightDirection.Up
                    )
                )
            elif momentum < -0.05:
                insights.append(
                    Insight.Price(
                        symbol,
                        timedelta(days=1),
                        InsightDirection.Down
                    )
                )

        return insights
```

---

### **4. Risk Agent** (Risk Management)

**Role:** Position sizing and risk controls

**Responsibilities:**
- Implement position sizing (volatility-based, equal weight, etc.)
- Add stop losses and take profits
- Create `Risk.py` module
- Ensure portfolio constraints

**LLM:** Sonnet 4.5 (nuanced reasoning for risk)

**Output:** `Risk.py`
```python
class RiskManagementModel:
    def __init__(self, algorithm, risk_per_trade=0.02):
        self.algorithm = algorithm
        self.risk_per_trade = risk_per_trade

    def ManageRisk(self, algorithm, targets):
        # Portfolio risk checks
        max_portfolio_leverage = 1.0
        max_position_size = 0.1  # 10% per position

        adjusted_targets = []
        total_exposure = 0

        for target in targets:
            # Calculate position size based on volatility
            volatility = self._calculate_volatility(target.Symbol)
            position_size = self.risk_per_trade / volatility

            # Apply constraints
            position_size = min(position_size, max_position_size)

            # Check total exposure
            if total_exposure + position_size > max_portfolio_leverage:
                continue

            adjusted_targets.append(
                PortfolioTarget(target.Symbol, position_size)
            )
            total_exposure += position_size

        return adjusted_targets

    def _calculate_volatility(self, symbol):
        # 20-day historical volatility
        history = self.algorithm.History(symbol, 20, Resolution.Daily)
        returns = history['close'].pct_change().dropna()
        return returns.std() * np.sqrt(252)
```

---

### **5. Strategy Agent** (Main Algorithm)

**Role:** Integrate all components into main algorithm

**Responsibilities:**
- Create `Main.py` with Initialize() and OnData()
- Wire up Universe, Alpha, Risk models
- Add logging and monitoring
- Ensure proper execution flow

**LLM:** Sonnet 4.5 or Devstral

**Output:** `Main.py`
```python
class MomentumStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2023, 12, 31)
        self.SetCash(100000)

        # Universe selection
        self.universe_model = CustomUniverseSelectionModel(self)
        self.SetUniverseSelection(self.universe_model)

        # Alpha model
        self.alpha_model = MomentumAlphaModel(self)
        self.SetAlpha(self.alpha_model)

        # Risk management
        self.risk_model = RiskManagementModel(self)
        self.SetRiskManagement(self.risk_model)

        # Portfolio construction
        self.SetPortfolioConstruction(
            EqualWeightingPortfolioConstructionModel()
        )

        # Execution
        self.SetExecution(
            ImmediateExecutionModel()
        )

        # Schedule rebalancing
        self.Schedule.On(
            self.DateRules.MonthStart(),
            self.TimeRules.AfterMarketOpen("SPY", 30),
            self.Rebalance
        )

    def Rebalance(self):
        self.Log(f"Rebalancing portfolio at {self.Time}")
        # Trigger alpha generation
        insights = self.alpha_model.Update(self, self.CurrentSlice)
        # Risk management will be applied automatically
```

---

### **6. Portfolio Agent** (Execution & Rebalancing)

**Role:** Portfolio construction and execution logic

**Responsibilities:**
- Implement rebalancing logic
- Handle execution timing
- Create `Portfolio.py` (if custom logic needed)
- Optimize for transaction costs

**LLM:** OSS-20B (efficient for standard patterns)

---

### **7. Integration Agent** (File Coordination)

**Role:** Ensure all files work together

**Responsibilities:**
- Check imports and dependencies
- Validate cross-file references
- Create `__init__.py` files
- Generate requirements.txt
- Create project structure

**LLM:** Sonnet 4.5 (architectural understanding)

**Output:** Complete project structure
```
momentum_strategy/
├── Main.py
├── Universe.py
├── Alpha.py
├── Risk.py
├── Portfolio.py
├── __init__.py
├── requirements.txt
└── README.md
```

---

## 🔌 MCP Server for QuantConnect

### **MCP Server Implementation**

```python
# quantcoder/mcp/quantconnect_server.py

import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent

class QuantConnectMCPServer:
    """MCP server for QuantConnect API integration"""

    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.server = Server("quantconnect")
        self._setup_tools()

    def _setup_tools(self):
        """Register MCP tools"""

        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="validate_code",
                    description="Validate QuantConnect algorithm code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "files": {"type": "object"}
                        }
                    }
                ),
                Tool(
                    name="backtest",
                    description="Run backtest in QuantConnect",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="get_api_docs",
                    description="Get QuantConnect API documentation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="deploy_live",
                    description="Deploy algorithm to live trading",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "algorithm_id": {"type": "string"},
                            "node_id": {"type": "string"}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "validate_code":
                return await self.validate_code(arguments)
            elif name == "backtest":
                return await self.backtest(arguments)
            elif name == "get_api_docs":
                return await self.get_api_docs(arguments)
            elif name == "deploy_live":
                return await self.deploy_live(arguments)

    async def validate_code(self, args):
        """Validate code against QuantConnect API"""
        # Use QuantConnect API to compile and validate
        response = await self._call_qc_api("/compile", {
            "code": args["code"],
            "files": args.get("files", {})
        })

        return [TextContent(
            type="text",
            text=json.dumps({
                "valid": response.get("success", False),
                "errors": response.get("errors", []),
                "warnings": response.get("warnings", [])
            })
        )]

    async def backtest(self, args):
        """Run backtest"""
        response = await self._call_qc_api("/backtests/create", {
            "projectId": args.get("project_id"),
            "compileId": args.get("compile_id"),
            "backtestName": f"QuantCoder_{datetime.now().isoformat()}"
        })

        backtest_id = response.get("backtestId")

        # Poll for completion
        while True:
            status = await self._call_qc_api(f"/backtests/read/{backtest_id}")
            if status.get("completed"):
                break
            await asyncio.sleep(2)

        return [TextContent(
            type="text",
            text=json.dumps({
                "backtest_id": backtest_id,
                "statistics": status.get("statistics", {}),
                "charts": status.get("charts", {}),
                "runtime_statistics": status.get("runtimeStatistics", {})
            })
        )]

    async def _call_qc_api(self, endpoint: str, data: dict = None):
        """Call QuantConnect API"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        async with aiohttp.ClientSession() as session:
            url = f"https://www.quantconnect.com/api/v2{endpoint}"

            if data:
                async with session.post(url, json=data, headers=headers) as resp:
                    return await resp.json()
            else:
                async with session.get(url, headers=headers) as resp:
                    return await resp.json()
```

---

## ⚡ Parallel Execution Framework

### **Async Tool Execution**

```python
# quantcoder/execution/parallel_executor.py

import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

class ParallelExecutor:
    """Execute tools and agents in parallel"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_agents_parallel(
        self,
        agent_tasks: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Execute multiple agents in parallel

        Args:
            agent_tasks: List of {"agent": AgentClass, "params": {...}}

        Returns:
            List of agent results
        """
        tasks = [
            self._run_agent_async(task["agent"], task["params"])
            for task in agent_tasks
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def _run_agent_async(self, agent, params):
        """Run single agent asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            agent.execute,
            **params
        )

    async def execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Execute multiple tools in parallel

        Args:
            tool_calls: List of {"tool": Tool, "params": {...}}

        Returns:
            List of tool results
        """
        tasks = [
            self._run_tool_async(call["tool"], call["params"])
            for call in tool_calls
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def _run_tool_async(self, tool, params):
        """Run single tool asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            tool.execute,
            **params
        )
```

---

## 🧠 Multi-LLM Support

### **LLM Provider Abstraction**

```python
# quantcoder/llm/providers.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate chat completion"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model identifier"""
        pass

class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages, temperature=0.7, max_tokens=2000):
        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.content[0].text

    def get_model_name(self):
        return f"anthropic/{self.model}"

class MistralProvider(LLMProvider):
    """Mistral (Devstral) provider"""

    def __init__(self, api_key: str, model: str = "devstral-2-123b"):
        from mistralai.client import MistralClient
        self.client = MistralClient(api_key=api_key)
        self.model = model

    async def chat(self, messages, temperature=0.7, max_tokens=2000):
        response = self.client.chat(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def get_model_name(self):
        return f"mistral/{self.model}"

class DeepSeekProvider(LLMProvider):
    """DeepSeek provider"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = model

    async def chat(self, messages, temperature=0.7, max_tokens=2000):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def get_model_name(self):
        return f"deepseek/{self.model}"

# Factory
class LLMFactory:
    """Create LLM providers"""

    @staticmethod
    def create(provider: str, api_key: str, model: Optional[str] = None):
        if provider == "anthropic":
            return AnthropicProvider(api_key, model or "claude-sonnet-4-5-20250929")
        elif provider == "mistral":
            return MistralProvider(api_key, model or "devstral-2-123b")
        elif provider == "deepseek":
            return DeepSeekProvider(api_key, model or "deepseek-chat")
        else:
            raise ValueError(f"Unknown provider: {provider}")
```

---

## 📁 Multi-File Code Generation

### **File Structure Manager**

```python
# quantcoder/codegen/multi_file.py

from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CodeFile:
    """Represents a generated code file"""
    filename: str
    content: str
    dependencies: List[str] = None

class MultiFileGenerator:
    """Generate multi-file QuantConnect projects"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.files: Dict[str, CodeFile] = {}

    def add_file(self, file: CodeFile):
        """Add a file to the project"""
        self.files[file.filename] = file

    def generate_project_structure(self, base_path: Path):
        """Generate complete project directory"""
        project_dir = base_path / self.project_name
        project_dir.mkdir(exist_ok=True, parents=True)

        # Write all files
        for filename, file in self.files.items():
            file_path = project_dir / filename
            file_path.write_text(file.content)

        # Generate __init__.py
        init_content = self._generate_init_file()
        (project_dir / "__init__.py").write_text(init_content)

        # Generate README
        readme_content = self._generate_readme()
        (project_dir / "README.md").write_text(readme_content)

        return project_dir

    def _generate_init_file(self) -> str:
        """Generate __init__.py with imports"""
        imports = []
        for filename in self.files.keys():
            if filename.endswith('.py') and filename != 'Main.py':
                module = filename[:-3]  # Remove .py
                imports.append(f"from .{module} import *")

        return "\n".join(imports)

    def _generate_readme(self) -> str:
        """Generate README.md"""
        return f"""# {self.project_name}

Generated by QuantCoder CLI v3.0

## Files

{chr(10).join(f"- **{f}**: {self._describe_file(f)}" for f in self.files.keys())}

## Usage

1. Upload this directory to QuantConnect
2. Set `Main.py` as the entry point
3. Run backtest

## Structure

This algorithm uses a modular structure:
- Universe selection logic in `Universe.py`
- Alpha signals in `Alpha.py`
- Risk management in `Risk.py`
- Main algorithm coordination in `Main.py`
"""

    def _describe_file(self, filename: str) -> str:
        """Describe file purpose"""
        descriptions = {
            "Main.py": "Main algorithm entry point",
            "Universe.py": "Universe selection model",
            "Alpha.py": "Alpha signal generation",
            "Risk.py": "Risk management model",
            "Portfolio.py": "Portfolio construction",
        }
        return descriptions.get(filename, "Supporting module")
```

---

## 🎯 Complete Workflow Example

```python
# Example: User request handling

User: "Create a momentum strategy with S&P 500 stocks,
       using 20-day momentum and 50-day MA filter,
       with 2% risk per trade"

# Step 1: Coordinator analyzes request
coordinator = CoordinatorAgent(llm=sonnet_4_5)
plan = coordinator.create_plan(user_request)

# Plan:
# {
#   "universe": "S&P 500 custom filter",
#   "alpha": "20-day momentum + 50-day MA",
#   "risk": "2% per trade",
#   "components": ["Universe", "Alpha", "Risk", "Main"],
#   "execution": "parallel"
# }

# Step 2: Spawn agents in parallel
executor = ParallelExecutor()

results = await executor.execute_agents_parallel([
    {
        "agent": UniverseAgent(llm=devstral),
        "params": {"criteria": "S&P 500, liquid stocks"}
    },
    {
        "agent": AlphaAgent(llm=devstral),
        "params": {"strategy": "20-day momentum + 50-day MA"}
    },
])

# Step 3: Sequential dependency (Risk needs Alpha output)
risk_result = RiskAgent(llm=sonnet_4_5).execute(
    risk_params="2% per trade",
    alpha_output=results[1]  # Alpha result
)

# Step 4: Integration
strategy_result = StrategyAgent(llm=sonnet_4_5).execute(
    universe=results[0],
    alpha=results[1],
    risk=risk_result
)

# Step 5: Validate via MCP
mcp_client = QuantConnectMCPClient()
validation = await mcp_client.validate_code(strategy_result.files)

if not validation.valid:
    # Step 6: Auto-fix
    fixed_code = await coordinator.fix_issues(
        strategy_result,
        validation.errors
    )
    validation = await mcp_client.validate_code(fixed_code.files)

# Step 7: Backtest
backtest = await mcp_client.backtest(
    strategy_result.files,
    start="2020-01-01",
    end="2023-12-31"
)

# Step 8: Deliver
return {
    "files": strategy_result.files,
    "validation": validation,
    "backtest": backtest,
    "sharpe": backtest.statistics.sharpe,
    "total_return": backtest.statistics.total_return
}
```

---

## 📊 Performance Expectations

| Task | Single Agent | Multi-Agent | Speedup |
|------|--------------|-------------|---------|
| Simple strategy (1 file) | 60s | 60s | 1x |
| Medium strategy (3 files) | 180s | 70s | **2.6x** |
| Complex strategy (5 files) | 300s | 90s | **3.3x** |
| With validation | 360s | 100s | **3.6x** |
| With backtest | 420s | 120s | **3.5x** |

---

## 🚀 Next Steps

1. Implement MCP server
2. Create specialized agents
3. Build parallel executor
4. Add multi-LLM support
5. Test complete workflow
6. Document and deploy

This architecture provides a **Claude Code-equivalent** system specifically optimized for QuantConnect!
