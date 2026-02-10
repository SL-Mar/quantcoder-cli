"""LLM handler — Ollama-only local inference.

Routes tasks to the appropriate local model via OllamaProvider:
  - Code generation / refinement / error fixing → qwen2.5-coder:14b
  - Summarization / chat → mistral
"""

import asyncio
import logging
import re
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
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

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

    # -- Two-pass summarization helpers ----------------------------------

    @staticmethod
    def _format_sections_for_prompt(
        sections: Dict[str, str], max_chars: int = 60000
    ) -> str:
        """Format paper sections into a single string within a token budget.

        Prioritizes methodology-relevant sections and truncates low-priority
        ones (acknowledgments, references, appendix) when over budget.
        """
        HIGH_PRIORITY_KEYWORDS = {
            "method", "model", "strategy", "trading", "signal", "algorithm",
            "approach", "result", "experiment", "implementation", "data",
            "feature", "regression", "portfolio", "backtest", "return",
            "risk", "parameter", "calibration", "estimation", "framework",
        }
        LOW_PRIORITY_KEYWORDS = {
            "acknowledg", "reference", "bibliography", "appendix", "vita",
            "disclosure", "funding", "supplementar",
        }

        def _priority(name: str) -> int:
            lower = name.lower()
            if any(kw in lower for kw in LOW_PRIORITY_KEYWORDS):
                return 2
            if any(kw in lower for kw in HIGH_PRIORITY_KEYWORDS):
                return 0
            return 1

        ordered = sorted(sections.items(), key=lambda kv: (_priority(kv[0]), kv[0]))

        parts: list[str] = []
        total = 0
        for name, text in ordered:
            header = f"\n### {name}\n"
            available = max_chars - total - len(header)
            if available <= 0:
                break
            chunk = text[:available]
            parts.append(header + chunk)
            total += len(header) + len(chunk)

        return "".join(parts)

    def extract_key_passages(self, sections: Dict[str, str]) -> Optional[str]:
        """Pass 1 — Extractive: quote verbatim passages relevant to implementation."""
        self.logger.info("Two-pass pipeline — Pass 1 (extract key passages)")

        formatted = self._format_sections_for_prompt(sections)
        if not formatted.strip():
            self.logger.warning("No section text to send to LLM")
            return None

        system = (
            "You are a quantitative finance research analyst. "
            "Read the paper sections below and QUOTE VERBATIM every passage that "
            "is relevant to implementing the described trading strategy or model. "
            "Do NOT paraphrase — copy the exact text. Do NOT skip passages because "
            "they use unfamiliar terms, novel formulas, or custom model names.\n\n"
            "Focus on:\n"
            "- Mathematical formulas and equations\n"
            "- Parameter values and calibration details\n"
            "- Entry and exit rules or signal generation logic\n"
            "- Risk controls, stop-loss rules, position sizing\n"
            "- Novel indicators or custom models (e.g., OU process, HMM, "
            "regime-switching, proprietary scores)\n"
            "- Universe selection and data requirements\n"
            "- Execution details (order types, rebalancing frequency)\n\n"
            "Output format: a numbered list of verbatim quotes, each preceded by "
            "the section name in brackets. Example:\n"
            "[Methodology] \"We define the signal as ...\"\n"
        )

        prompt = f"Extract all implementable passages from this paper:\n{formatted}"

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            result = _run_async(
                self._summary_llm.chat(
                    messages=messages, max_tokens=4096, temperature=0.1
                )
            )
            self.logger.info(
                f"Pass 1 complete — extracted {len(result)} chars of passages"
            )
            return result
        except Exception as e:
            self.logger.error(f"Pass 1 (extract_key_passages) failed: {e}")
            return None

    def interpret_strategy(self, extractions: str) -> Optional[str]:
        """Pass 2 — Interpretive: convert verbatim quotes into strategy spec."""
        self.logger.info("Two-pass pipeline — Pass 2 (interpret strategy)")

        if not extractions or not extractions.strip():
            self.logger.warning("Empty extractions — nothing to interpret")
            return None

        system = (
            "You are a quantitative trading strategist. Convert the verbatim "
            "paper quotes below into a precise, implementable strategy "
            "specification. Base your output ONLY on what the quotes say. "
            "If the paper uses an OU process, specify an OU process — do NOT "
            "substitute RSI or SMA. If the paper describes a proprietary model "
            "or custom indicator, describe it faithfully.\n\n"
            "Use the following flexible structure. Skip any section that is "
            "genuinely irrelevant to this particular strategy:\n\n"
            "## STRATEGY OVERVIEW\n"
            "One paragraph summarizing the core idea.\n\n"
            "## MATHEMATICAL MODEL\n"
            "Formulas, distributions, state dynamics — as described in the paper.\n\n"
            "## SIGNAL GENERATION\n"
            "Exact entry/exit conditions with numeric thresholds.\n\n"
            "## EXIT RULES\n"
            "Stop loss, profit target, time stop, trailing stop — with exact values.\n\n"
            "## RISK MANAGEMENT\n"
            "Position sizing, max exposure, drawdown limits.\n\n"
            "## UNIVERSE / STOCK SELECTION\n"
            "Market, filters, number of instruments.\n\n"
            "## EXECUTION DETAILS\n"
            "Order types, rebalancing frequency, data resolution.\n\n"
            "## PARAMETER TABLE\n"
            "| Parameter | Value | Source |\n"
            "|-----------|-------|--------|\n"
            "Every numeric parameter from the paper with source attribution.\n"
        )

        prompt = (
            "Convert these verbatim paper extractions into an implementable "
            f"strategy specification:\n\n{extractions}"
        )

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            result = _run_async(
                self._summary_llm.chat(
                    messages=messages, max_tokens=4096, temperature=0.3
                )
            )
            self.logger.info(
                f"Pass 2 complete — strategy spec is {len(result)} chars"
            )
            return result
        except Exception as e:
            self.logger.error(f"Pass 2 (interpret_strategy) failed: {e}")
            return None

    # -- Legacy single-pass summary (kept intact) -------------------------

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

    # -- Fidelity assessment ---------------------------------------------------

    @staticmethod
    def _parse_fidelity_response(response: str) -> Dict:
        """Parse structured fidelity assessment from mistral's response.

        Expected format in response:
            FAITHFUL: YES/NO
            SCORE: 1-5
            ISSUES: - issue1 / - issue2
            CORRECTION_PLAN: free text
        """
        result = {
            "faithful": False,
            "score": 1,
            "issues": [],
            "correction_plan": "",
        }

        if not response:
            return result

        # FAITHFUL
        m = re.search(r"FAITHFUL\s*:\s*(YES|NO)", response, re.IGNORECASE)
        if m:
            result["faithful"] = m.group(1).upper() == "YES"

        # SCORE
        m = re.search(r"SCORE\s*:\s*(\d)", response)
        if m:
            score = int(m.group(1))
            result["score"] = max(1, min(5, score))

        # ISSUES — collect bullet lines between ISSUES: and CORRECTION_PLAN:
        m = re.search(
            r"ISSUES\s*:(.*?)(?:CORRECTION_PLAN|$)", response, re.DOTALL | re.IGNORECASE
        )
        if m:
            issues_block = m.group(1)
            issues = re.findall(r"-\s*(.+)", issues_block)
            result["issues"] = [i.strip() for i in issues if i.strip()]

        # CORRECTION_PLAN
        m = re.search(r"CORRECTION_PLAN\s*:(.*)", response, re.DOTALL | re.IGNORECASE)
        if m:
            result["correction_plan"] = m.group(1).strip()

        # Reconcile: if score >= 3 and FAITHFUL wasn't explicitly NO, treat as faithful
        if result["score"] >= 3 and not re.search(
            r"FAITHFUL\s*:\s*NO", response, re.IGNORECASE
        ):
            result["faithful"] = True

        return result

    def assess_fidelity(self, summary: str, code: str) -> Dict:
        """Use the reasoning LLM (mistral) to evaluate whether code implements the summary.

        Returns dict with keys: faithful (bool), score (1-5), issues (list), correction_plan (str).
        """
        self.logger.info("Assessing fidelity of generated code against summary")

        system = (
            "You are a quantitative finance code reviewer. You are given a strategy "
            "specification (SUMMARY) and generated QuantConnect Python code (CODE).\n\n"
            "Evaluate whether the CODE faithfully implements the mathematical model "
            "and trading logic described in the SUMMARY.\n\n"
            "Check specifically:\n"
            "1. Does the code implement the EXACT model described (e.g., OU process, "
            "HMM, regime-switching, jump-diffusion) — or does it substitute a generic "
            "indicator (RSI, SMA) instead?\n"
            "2. Are the parameters from the summary used in the code?\n"
            "3. Does the code use custom logic (numpy, manual calculations, "
            "PythonIndicator, RollingWindow) when the model requires it?\n"
            "4. Are entry/exit conditions consistent with the summary?\n\n"
            "Respond in EXACTLY this format:\n"
            "FAITHFUL: YES or NO\n"
            "SCORE: 1-5 (1=completely wrong model, 3=partial match, 5=exact)\n"
            "ISSUES:\n"
            "- issue 1\n"
            "- issue 2\n"
            "CORRECTION_PLAN:\n"
            "Describe what the code should change to faithfully implement the summary."
        )

        prompt = f"SUMMARY:\n{summary}\n\nCODE:\n{code}"

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            response = _run_async(
                self._summary_llm.chat(
                    messages=messages, max_tokens=2048, temperature=0.1
                )
            )
            result = self._parse_fidelity_response(response)
            self.logger.info(
                f"Fidelity assessment: faithful={result['faithful']}, "
                f"score={result['score']}, issues={len(result['issues'])}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Fidelity assessment failed: {e}")
            return {"faithful": False, "score": 1, "issues": [str(e)], "correction_plan": ""}

    def regenerate_with_critique(
        self, summary: str, code: str, critique: Dict
    ) -> Optional[str]:
        """Regenerate code using the coding LLM with structured critique feedback.

        Args:
            summary: The strategy specification.
            code: The previous (unfaithful) generated code.
            critique: Dict from assess_fidelity with issues and correction_plan.

        Returns:
            New code string, or None on failure.
        """
        self.logger.info("Regenerating code with fidelity critique")

        issues_text = "\n".join(f"- {i}" for i in critique.get("issues", []))
        correction_plan = critique.get("correction_plan", "")

        system = (
            "You are an expert QuantConnect algorithm developer. You previously "
            "generated code that did NOT faithfully implement the strategy. "
            "A reviewer found specific issues. Fix ALL of them.\n\n"
            "CRITICAL RULES:\n"
            "1. ALWAYS start with: from AlgorithmImports import *\n"
            "2. Class must inherit from QCAlgorithm\n"
            "3. Use snake_case methods: self.set_start_date(), self.add_equity(), etc.\n"
            "4. Return ONLY Python code, no markdown, no explanations\n\n"
            "WHEN THE STRATEGY REQUIRES A CUSTOM MODEL (OU process, HMM, "
            "regime-switching, jump-diffusion, etc.):\n"
            "- Import numpy as np inside the algorithm file\n"
            "- Use self.history() to get price history as a DataFrame\n"
            "- Implement the mathematical model directly with numpy operations\n"
            "- Use RollingWindow[float] or plain lists to maintain state\n"
            "- Do NOT substitute RSI, SMA, or other standard indicators unless "
            "the strategy explicitly calls for them\n"
            "- Create helper methods on the class for model calculations\n"
        )

        prompt = (
            f"STRATEGY SPECIFICATION:\n{summary}\n\n"
            f"PREVIOUS CODE (unfaithful — do not copy its approach):\n{code}\n\n"
            f"REVIEWER ISSUES:\n{issues_text}\n\n"
            f"CORRECTION PLAN:\n{correction_plan}\n\n"
            "Generate a completely revised QuantConnect algorithm that faithfully "
            "implements the strategy specification. Return ONLY Python code."
        )

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            new_code = _run_async(
                self._code_llm.chat(
                    messages=messages, max_tokens=self.max_tokens, temperature=0.3
                )
            )
            self.logger.info("Regenerated code with critique feedback")
            return self._strip_markdown(new_code) if new_code else None
        except Exception as e:
            self.logger.error(f"Regeneration with critique failed: {e}")
            return None

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown code fences from LLM output."""
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return text
