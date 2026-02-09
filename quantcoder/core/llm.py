"""LLM handler — Ollama-only local inference.

Routes tasks to the appropriate local model via OllamaProvider:
  - Code generation / refinement / error fixing → qwen2.5-coder:32b
  - Summarization / chat → mistral
"""

import asyncio
import logging
from typing import Dict, List, Optional

from quantcoder.llm import LLMFactory

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop — create a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class LLMHandler:
    """Handles interactions with Ollama LLM providers."""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Read Ollama settings from config
        base_url = getattr(config.model, 'ollama_base_url', 'http://localhost:11434')
        timeout = getattr(config.model, 'ollama_timeout', 600)

        # Task-specific providers
        self._code_llm = LLMFactory.create(
            task="coding",
            model=getattr(config.model, 'code_model', None),
            base_url=base_url,
            timeout=timeout,
        )
        self._chat_llm = LLMFactory.create(
            task="chat",
            model=getattr(config.model, 'reasoning_model', None),
            base_url=base_url,
            timeout=timeout,
        )
        self._summary_llm = LLMFactory.create(
            task="summary",
            model=getattr(config.model, 'reasoning_model', None),
            base_url=base_url,
            timeout=timeout,
        )

        self.temperature = config.model.temperature
        self.max_tokens = config.model.max_tokens

        self.logger.info(
            f"LLMHandler initialized — "
            f"code: {self._code_llm.get_model_name()}, "
            f"chat: {self._chat_llm.get_model_name()}, "
            f"summary: {self._summary_llm.get_model_name()}"
        )

    def generate_summary(self, extracted_data: Dict[str, List[str]]) -> Optional[str]:
        """Generate a structured trading strategy summary for algorithm generation."""
        self.logger.info("Generating summary")

        trading_signals = '\n'.join(extracted_data.get('trading_signal', []))
        risk_management = '\n'.join(extracted_data.get('risk_management', []))
        strategy_params = '\n'.join(extracted_data.get('strategy_parameters', []))

        system = """You are a quantitative trading strategist. Your job is to extract PRECISE, IMPLEMENTABLE trading rules from research paper excerpts. Output structured specifications that a programmer can directly convert into code. Never be vague — if the paper doesn't specify a parameter, state a reasonable default with justification."""

        prompt = f"""Extract a complete, implementable trading strategy specification from the following research paper excerpts.

### TRADING SIGNALS FROM PAPER:
{trading_signals}

### RISK MANAGEMENT FROM PAPER:
{risk_management}

### STRATEGY PARAMETERS FROM PAPER:
{strategy_params}

---

Provide your output in EXACTLY this structured format (fill every section):

## INDICATORS
List each indicator with exact parameters:
- Name: [e.g., RSI]
- Period: [e.g., 14]
- Timeframe: [e.g., Daily, Minute]
- Thresholds: [e.g., oversold < 30, overbought > 70]

## ENTRY RULES
Write as precise conditional logic:
- LONG entry: IF [condition1] AND [condition2] THEN BUY
- SHORT entry: IF [condition1] AND [condition2] THEN SELL SHORT
- Include exact threshold values, not vague descriptions

## EXIT RULES
- Stop loss: [exact % or ATR multiple, e.g., 2% below entry or 1.5x ATR]
- Profit target: [exact % or ATR multiple, e.g., 5% above entry or 3x ATR]
- Time stop: [e.g., liquidate at 3:55 PM ET, or hold max 5 days]
- Trailing stop: [if applicable, exact parameters]

## POSITION SIZING
- Method: [fixed dollar, % of portfolio, Kelly criterion, etc.]
- Size: [exact value, e.g., $10,000 per position or 2% of portfolio]
- Max concurrent positions: [number]
- Max portfolio exposure: [% or dollar amount]

## UNIVERSE / STOCK SELECTION
- Market: [US equities, futures, crypto, etc.]
- Filters: [market cap > $X, avg volume > Y shares, sector = Z]
- Number of stocks: [fixed watchlist or dynamic screening]

## TIMEFRAME
- Data resolution: [Daily, Minute, Hour]
- Trading frequency: [intraday, daily rebalance, weekly]
- Holding period: [typical duration]

## BACKTEST PARAMETERS
- Suggested start date: [YYYY-MM-DD or relative like "3 months ago"]
- Suggested end date: [YYYY-MM-DD or "today"]
- Initial capital: [$100,000 unless paper specifies otherwise]
- Benchmark: [SPY unless paper specifies otherwise]"""

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            summary = _run_async(
                self._summary_llm.chat(messages=messages, max_tokens=4096, temperature=0.3)
            )
            self.logger.info("Summary generated successfully")
            return summary
        except Exception as e:
            self.logger.error(f"Error during summary generation: {e}")
            return None

    def generate_qc_code(self, summary: str) -> Optional[str]:
        """Generate QuantConnect Python code."""
        self.logger.info("Generating QuantConnect code")

        system = """You are an expert QuantConnect algorithm developer. You write production-quality LEAN Python algorithms.

CRITICAL RULES:
1. ALWAYS start with: from AlgorithmImports import *
2. Class must inherit from QCAlgorithm
3. Use snake_case methods: self.set_start_date(), self.set_cash(), self.add_equity(), etc.
4. Register indicators via self methods, NOT standalone constructors
5. Always check indicator.is_ready before using .current.value
6. Use self.set_holdings() for position sizing or self.market_order() for discrete orders
7. NEVER invent indicators or classes that don't exist in QuantConnect
8. Return ONLY Python code, no markdown, no explanations

INDICATOR SIGNATURES (these are EXACT - do NOT omit parameters):
- self.sma(symbol, period, resolution) -> 3 args
- self.ema(symbol, period, resolution) -> 3 args
- self.rsi(symbol, period, moving_average_type, resolution) -> 4 args, e.g. self.rsi(symbol, 14, MovingAverageType.WILDERS, Resolution.DAILY)
- self.atr(symbol, period, moving_average_type, resolution) -> 4 args, e.g. self.atr(symbol, 14, MovingAverageType.SIMPLE, Resolution.DAILY)
- self.macd(symbol, fast_period, slow_period, signal_period, moving_average_type, resolution) -> 6 args
- self.bb(symbol, period, k, moving_average_type, resolution) -> 5 args
- self.momp(symbol, period, resolution) -> 3 args
- self.adx(symbol, period, resolution) -> 3 args

COMMON PITFALLS TO AVOID:
- ATR requires MovingAverageType parameter (4 args, NOT 3)
- RSI requires MovingAverageType parameter (4 args, NOT 3)
- MACD requires MovingAverageType parameter
- Do NOT use standalone constructors like ATR(14), SMA(20) - always use self.atr(), self.sma()
- Do NOT reference self.symbol unless you defined it - use the symbol variable from add_equity()
- Do NOT use has_data - use data.contains_key(symbol) in on_data, or check price > 0"""

        prompt = f"""Convert this trading strategy into a complete QuantConnect Python algorithm:

{summary}

The algorithm must:
- Use from AlgorithmImports import * as the only import
- Set start_date, end_date, and cash in initialize()
- Add securities with self.add_equity()
- Register indicators using self methods (e.g., self._rsi = self.rsi(symbol, 14))
- Implement on_data(self, data) with entry/exit logic
- Include stop loss and position sizing
- Be ready to compile and run without errors"""

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            code = _run_async(
                self._code_llm.chat(messages=messages, max_tokens=self.max_tokens, temperature=0.3)
            )
            self.logger.info(f"Code generated with {self._code_llm.get_model_name()}")
        except Exception as e:
            self.logger.error(f"Error during code generation: {e}")
            return None

        return self._strip_markdown(code)

    def refine_code(self, code: str) -> Optional[str]:
        """Fix errors in generated QuantConnect code."""
        self.logger.info("Refining generated code")

        system = """You are an expert QuantConnect LEAN Python debugger. Fix the code so it compiles and runs without errors.

CRITICAL RULES:
1. ALWAYS start with: from AlgorithmImports import *
2. Use snake_case methods: set_start_date, add_equity, set_holdings, etc.
3. Use ONLY real QuantConnect indicators registered via self methods
4. Return ONLY the corrected Python code, no markdown, no explanations"""

        prompt = f"""Fix this QuantConnect Python algorithm. It may have import errors, undefined variables, or use non-existent QuantConnect classes/methods.

{code}

Return ONLY the corrected Python code."""

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            corrected = _run_async(
                self._code_llm.chat(messages=messages, max_tokens=self.max_tokens, temperature=0.2)
            )
            self.logger.info(f"Code refined with {self._code_llm.get_model_name()}")
        except Exception as e:
            self.logger.error(f"Error during code refinement: {e}")
            return None

        return self._strip_markdown(corrected)

    def fix_runtime_error(self, code: str, error_message: str) -> Optional[str]:
        """Fix a QuantConnect runtime error by feeding the error back to the LLM."""
        self.logger.info(f"Fixing runtime error: {error_message[:100]}")

        system = """You are an expert QuantConnect LEAN Python debugger.
You are given algorithm code and the EXACT runtime error from QuantConnect's cloud.
Fix the code so it runs without errors.

CRITICAL RULES:
1. ALWAYS start with: from AlgorithmImports import *
2. Use snake_case methods: set_start_date, add_equity, set_holdings, etc.
3. Use ONLY real QuantConnect indicators registered via self methods

INDICATOR SIGNATURES (EXACT - do NOT omit parameters):
- self.sma(symbol, period, resolution) -> 3 args
- self.ema(symbol, period, resolution) -> 3 args
- self.rsi(symbol, period, moving_average_type, resolution) -> 4 args
- self.atr(symbol, period, moving_average_type, resolution) -> 4 args
- self.macd(symbol, fast, slow, signal, moving_average_type, resolution) -> 6 args
- self.bb(symbol, period, k, moving_average_type, resolution) -> 5 args
- self.momp(symbol, period, resolution) -> 3 args
- self.adx(symbol, period, resolution) -> 3 args

MovingAverageType options: SIMPLE, EXPONENTIAL, WILDERS, TRIANGULAR

4. Return ONLY the corrected Python code, no markdown, no explanations"""

        prompt = f"""This QuantConnect algorithm crashed with the following runtime error:

ERROR:
{error_message}

ALGORITHM CODE:
{code}

Fix the error and return ONLY the corrected Python code."""

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            corrected = _run_async(
                self._code_llm.chat(messages=messages, max_tokens=8192, temperature=0.2)
            )
        except Exception as e:
            self.logger.error(f"Error during runtime fix: {e}")
            return None

        return self._strip_markdown(corrected) if corrected else None

    def chat(self, message: str, context: Optional[List[Dict]] = None) -> Optional[str]:
        """Chat conversation using the reasoning model."""
        self.logger.info("Chatting with LLM")

        messages = context or []
        messages.append({"role": "user", "content": message})

        try:
            return _run_async(
                self._chat_llm.chat(
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            )
        except Exception as e:
            self.logger.error(f"Error during chat: {e}")
            return None

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown code fences from LLM output."""
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return text
