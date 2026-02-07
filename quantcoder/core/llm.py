"""LLM handler supporting multiple providers.

Uses Ollama for chat/summarize (free, fast) and Claude for code generation (quality).
"""

import os
import logging
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMHandler:
    """Handles interactions with LLM providers."""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        provider = config.model.provider

        if provider == "ollama":
            base_url = config.model.ollama_base_url
            self.client = OpenAI(base_url=base_url, api_key="ollama")
            self.model = config.model.ollama_model
            self.logger.info(f"Using Ollama provider: {base_url}, model={self.model}")
        else:
            api_key = config.api_key or config.load_api_key()
            self.client = OpenAI(api_key=api_key)
            self.model = config.model.model

        self.temperature = config.model.temperature
        self.max_tokens = config.model.max_tokens

        # Code generation provider: "anthropic" or "ollama" (from config)
        self.code_provider = getattr(config.model, 'code_provider', 'anthropic')
        self._code_client = None
        self._code_model = "claude-opus-4-6"
        self.logger.info(f"Code generation provider: {self.code_provider}")

        # Summary provider: "anthropic" or "ollama" (from config)
        self.summary_provider = getattr(config.model, 'summary_provider', 'ollama')
        self._summary_model = getattr(config.model, 'summary_model', 'claude-sonnet-4-5-20250929')
        self.logger.info(f"Summary provider: {self.summary_provider}")

    def _get_code_client(self):
        """Lazy-init Anthropic client for code generation."""
        if self.code_provider != "anthropic":
            return None

        if self._code_client is None:
            from dotenv import load_dotenv
            env_path = self.config.home_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path)

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                import anthropic
                self._code_client = anthropic.Anthropic(api_key=api_key)
                self.logger.info(f"Claude code generation enabled: {self._code_model}")
            else:
                self.logger.warning("ANTHROPIC_API_KEY not found, falling back to Ollama for code gen")

        return self._code_client

    def _generate_with_claude(self, system: str, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Generate text using Claude API."""
        client = self._get_code_client()
        if not client:
            return None

        try:
            response = client.messages.create(
                model=self._code_model,
                max_tokens=8192,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            return None

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

        # Route through Claude if configured
        if self.summary_provider == "anthropic":
            self.logger.info(f"Using Claude ({self._summary_model}) for summarization")
            summary = self._generate_summary_with_claude(system, prompt)
            if summary:
                self.logger.info("Summary generated with Claude")
                return summary
            self.logger.warning("Claude summary failed, falling back to Ollama")

        # Ollama fallback / default path
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()
            self.logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            self.logger.error(f"Error during summary generation: {e}")
            return None

    def _generate_summary_with_claude(self, system: str, prompt: str) -> Optional[str]:
        """Generate summary using Claude API (reuses the Anthropic client from code gen)."""
        client = self._get_code_client()
        if not client:
            return None

        try:
            response = client.messages.create(
                model=self._summary_model,
                max_tokens=4096,
                temperature=0.3,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            self.logger.error(f"Claude summary API error: {e}")
            return None

    def generate_qc_code(self, summary: str) -> Optional[str]:
        """Generate QuantConnect Python code using Claude Opus."""
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

        # Try Claude first
        code = self._generate_with_claude(system, prompt, temperature=0.3)

        if code:
            self.logger.info("Code generated with Claude Opus")
        else:
            # Fallback to default provider
            self.logger.info("Falling back to default provider for code generation")
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.3
                )
                code = response.choices[0].message.content.strip()
            except Exception as e:
                self.logger.error(f"Error during code generation: {e}")
                return None

        # Clean up markdown formatting
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    def refine_code(self, code: str) -> Optional[str]:
        """Fix errors in generated QuantConnect code using Claude Opus."""
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

        # Try Claude first
        corrected = self._generate_with_claude(system, prompt, temperature=0.2)

        if corrected:
            self.logger.info("Code refined with Claude Opus")
        else:
            # Fallback to default provider
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.2
                )
                corrected = response.choices[0].message.content.strip()
            except Exception as e:
                self.logger.error(f"Error during code refinement: {e}")
                return None

        # Clean up markdown formatting
        if "```python" in corrected:
            corrected = corrected.split("```python")[1].split("```")[0].strip()
        elif "```" in corrected:
            corrected = corrected.split("```")[1].split("```")[0].strip()

        return corrected

    def fix_runtime_error(self, code: str, error_message: str) -> Optional[str]:
        """Fix a QuantConnect runtime error by feeding the error back to Claude."""
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

        corrected = self._generate_with_claude(system, prompt, temperature=0.2)

        if not corrected:
            # Fallback to default provider
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=8192,
                    temperature=0.2
                )
                corrected = response.choices[0].message.content.strip()
            except Exception as e:
                self.logger.error(f"Error during runtime fix: {e}")
                return None

        if corrected:
            if "```python" in corrected:
                corrected = corrected.split("```python")[1].split("```")[0].strip()
            elif "```" in corrected:
                corrected = corrected.split("```")[1].split("```")[0].strip()

        return corrected

    def chat(self, message: str, context: Optional[List[Dict]] = None) -> Optional[str]:
        """Chat conversation using the default provider (Ollama)."""
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
