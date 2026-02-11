"""Post-generation QC API linter.

Static analysis and auto-fix for common QuantConnect API mistakes
produced by local LLMs (wrong casing, C# patterns, indicator shadowing, etc.).
Runs between code generation and QC compilation to avoid wasting backtest attempts.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class LintIssue:
    rule_id: str       # "QC001"–"QC010"
    line: int
    message: str
    severity: str      # "error" | "warning"
    fixed: bool
    original: str
    replacement: str


@dataclass
class LintResult:
    code: str
    issues: List[LintIssue] = field(default_factory=list)

    @property
    def had_fixes(self) -> bool:
        return any(i.fixed for i in self.issues)

    @property
    def unfixable_count(self) -> int:
        return sum(1 for i in self.issues if not i.fixed)

    @property
    def unfixable_hints(self) -> List[str]:
        return [i.message for i in self.issues if not i.fixed]


# ---------------------------------------------------------------------------
# QC001 — PascalCase API methods/attributes/defs
# ---------------------------------------------------------------------------

# self.Method() → self.method()
_METHOD_MAP = {
    "SetStartDate": "set_start_date",
    "SetEndDate": "set_end_date",
    "SetCash": "set_cash",
    "SetBenchmark": "set_benchmark",
    "SetBrokerageModel": "set_brokerage_model",
    "SetWarmUp": "set_warm_up",
    "SetWarmup": "set_warmup",
    "AddEquity": "add_equity",
    "AddForex": "add_forex",
    "AddCrypto": "add_crypto",
    "AddFuture": "add_future",
    "AddOption": "add_option",
    "AddSecurity": "add_security",
    "MarketOrder": "market_order",
    "LimitOrder": "limit_order",
    "StopMarketOrder": "stop_market_order",
    "StopLimitOrder": "stop_limit_order",
    "MarketOnOpenOrder": "market_on_open_order",
    "MarketOnCloseOrder": "market_on_close_order",
    "Liquidate": "liquidate",
    "SetHoldings": "set_holdings",
    "Log": "log",
    "Debug": "debug",
    "Error": "error",
    "Quit": "quit",
    "Plot": "plot",
    "Record": "record",
    "RegisterIndicator": "register_indicator",
    "WarmUpIndicator": "warm_up_indicator",
    "History": "history",
    "SMA": "sma",
    "EMA": "ema",
    "RSI": "rsi",
    "MACD": "macd",
    "BB": "bb",
    "ATR": "atr",
    "ADX": "adx",
    "MOM": "mom",
    "ROC": "roc",
    "MOMP": "momp",
    "STD": "std",
    "MIN": "min",  # note: only match self.MIN(
    "MAX": "max",  # note: only match self.MAX(
}

# .Attribute → .attribute
_ATTR_MAP = {
    ".IsReady": ".is_ready",
    ".Price": ".price",
    ".Value": ".value",
    ".Current": ".current",
    ".Symbol": ".symbol",
    ".Invested": ".invested",
    ".Quantity": ".quantity",
    ".AveragePrice": ".average_price",
    ".UnrealizedProfit": ".unrealized_profit",
    ".TotalPortfolioValue": ".total_portfolio_value",
    ".Cash": ".cash",
    ".Open": ".open",
    ".High": ".high",
    ".Low": ".low",
    ".Close": ".close",
    ".Volume": ".volume",
}

# self.Attr.Method( → self.attr.method( (chained scheduling API)
# Ordered longest-first to avoid partial matches (EveryDay before Every)
_CHAINED_MAP = {
    "self.Schedule.On": "self.schedule.on",
    "self.DateRules.EveryDay": "self.date_rules.every_day",
    "self.DateRules.MonthStart": "self.date_rules.month_start",
    "self.DateRules.MonthEnd": "self.date_rules.month_end",
    "self.DateRules.WeekStart": "self.date_rules.week_start",
    "self.DateRules.WeekEnd": "self.date_rules.week_end",
    "self.DateRules.Every": "self.date_rules.every",
    "self.TimeRules.AfterMarketOpen": "self.time_rules.after_market_open",
    "self.TimeRules.BeforeMarketClose": "self.time_rules.before_market_close",
    "self.TimeRules.At": "self.time_rules.at",
    "self.TimeRules.Every": "self.time_rules.every",
}

# def MethodName(self → def method_name(self
_DEF_MAP = {
    "Initialize": "initialize",
    "OnData": "on_data",
    "OnOrderEvent": "on_order_event",
    "OnEndOfDay": "on_end_of_day",
    "OnSecuritiesChanged": "on_securities_changed",
    "OnWarmupFinished": "on_warmup_finished",
}


def _rule_qc001(code: str, issues: List[LintIssue]) -> str:
    """Fix PascalCase API calls."""
    # Method calls: self.PascalCase(
    for pascal, snake in _METHOD_MAP.items():
        pattern = re.compile(r'self\.' + pascal + r'(?=\s*\()')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC001", line=lineno,
                message=f"PascalCase method self.{pascal}() → self.{snake}()",
                severity="error", fixed=True,
                original=m.group(), replacement=f"self.{snake}",
            ))
        code = pattern.sub(f"self.{snake}", code)

    # Attribute access: .PascalAttr (not followed by '(' — that's a method)
    # Use word boundary to avoid .Value matching .Values
    for pascal, snake in _ATTR_MAP.items():
        pattern = re.compile(re.escape(pascal) + r'(?![a-zA-Z0-9_]|\s*\()')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC001", line=lineno,
                message=f"PascalCase attribute {pascal} → {snake}",
                severity="error", fixed=True,
                original=m.group(), replacement=snake,
            ))
        code = pattern.sub(snake, code)

    # Chained scheduling API: self.Schedule.On( → self.schedule.on(
    for pascal, snake in _CHAINED_MAP.items():
        pattern = re.compile(re.escape(pascal) + r'(?=\s*\()')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC001", line=lineno,
                message=f"PascalCase chained API {pascal}() → {snake}()",
                severity="error", fixed=True,
                original=m.group(), replacement=snake,
            ))
        code = pattern.sub(snake, code)

    # RollingWindow .Add( → .add(
    rw_names = set(_RW_DECL.findall(code))
    for name in rw_names:
        pattern = re.compile(r'(self\.' + re.escape(name) + r')\.Add(?=\s*\()')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC001", line=lineno,
                message=f"self.{name}.Add() → self.{name}.add() (RollingWindow)",
                severity="error", fixed=True,
                original=f"self.{name}.Add", replacement=f"self.{name}.add",
            ))
        code = pattern.sub(rf'\1.add', code)

    # Method definitions: def PascalCase(self
    for pascal, snake in _DEF_MAP.items():
        pattern = re.compile(r'(def\s+)' + pascal + r'(\s*\(\s*self)')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC001", line=lineno,
                message=f"PascalCase def {pascal} → {snake}",
                severity="error", fixed=True,
                original=f"def {pascal}", replacement=f"def {snake}",
            ))
        code = pattern.sub(rf'\g<1>{snake}\2', code)

    return code


# ---------------------------------------------------------------------------
# QC007 — Resolution casing (run early so other rules see normalized code)
# ---------------------------------------------------------------------------

_RESOLUTION_MAP = {
    "Resolution.Tick": "Resolution.TICK",
    "Resolution.Second": "Resolution.SECOND",
    "Resolution.Minute": "Resolution.MINUTE",
    "Resolution.Hour": "Resolution.HOUR",
    "Resolution.Daily": "Resolution.DAILY",
}


def _rule_qc007(code: str, issues: List[LintIssue]) -> str:
    """Fix wrong Resolution casing."""
    for wrong, correct in _RESOLUTION_MAP.items():
        pattern = re.compile(re.escape(wrong) + r'(?![a-zA-Z])')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC007", line=lineno,
                message=f"Resolution casing {wrong} → {correct}",
                severity="error", fixed=True,
                original=wrong, replacement=correct,
            ))
        code = pattern.sub(correct, code)
    return code


# ---------------------------------------------------------------------------
# QC004 — Action() wrapper on scheduled callbacks
# ---------------------------------------------------------------------------

def _rule_qc004(code: str, issues: List[LintIssue]) -> str:
    """Remove Action() wrappers (C# pattern)."""
    pattern = re.compile(r'Action\(\s*(self\.\w+)\s*\)')
    for m in pattern.finditer(code):
        lineno = code[:m.start()].count('\n') + 1
        issues.append(LintIssue(
            rule_id="QC004", line=lineno,
            message=f"Action() wrapper not needed in Python: Action({m.group(1)}) → {m.group(1)}",
            severity="error", fixed=True,
            original=m.group(), replacement=m.group(1),
        ))
    code = pattern.sub(r'\1', code)
    return code


# ---------------------------------------------------------------------------
# QC002 — len() on RollingWindow
# ---------------------------------------------------------------------------

# Match patterns like: self.xyz = RollingWindow[...](...) to find RW var names
_RW_DECL = re.compile(r'self\.(\w+)\s*=\s*RollingWindow\s*\[')


def _rule_qc002(code: str, issues: List[LintIssue]) -> str:
    """Replace len(rolling_window) with rolling_window.count."""
    rw_names = set(_RW_DECL.findall(code))
    if not rw_names:
        return code

    for name in rw_names:
        pattern = re.compile(r'len\(\s*self\.' + re.escape(name) + r'\s*\)')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC002", line=lineno,
                message=f"len(self.{name}) → self.{name}.count (RollingWindow)",
                severity="error", fixed=True,
                original=m.group(), replacement=f"self.{name}.count",
            ))
        code = pattern.sub(f"self.{name}.count", code)

    return code


# ---------------------------------------------------------------------------
# QC003 — .Values on RollingWindow
# ---------------------------------------------------------------------------

def _rule_qc003(code: str, issues: List[LintIssue]) -> str:
    """Replace rolling_window.Values with list(rolling_window)."""
    rw_names = set(_RW_DECL.findall(code))
    if not rw_names:
        return code

    for name in rw_names:
        pattern = re.compile(r'self\.' + re.escape(name) + r'\.Values\b')
        for m in pattern.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC003", line=lineno,
                message=f"self.{name}.Values → list(self.{name}) (RollingWindow)",
                severity="error", fixed=True,
                original=m.group(), replacement=f"list(self.{name})",
            ))
        code = pattern.sub(f"list(self.{name})", code)

    return code


# ---------------------------------------------------------------------------
# QC005 — History DataFrame treated as Slice (warning only)
# ---------------------------------------------------------------------------

_HISTORY_SLICE_PATTERNS = [
    # .Bars[ is valid Slice access in on_data — only flag History-specific C# patterns
    re.compile(r'\.ForEach\s*\('),
    re.compile(r'\.GetValue\s*\('),
]


def _rule_qc005(code: str, issues: List[LintIssue]) -> str:
    """Warn about C# History iteration patterns."""
    for pat in _HISTORY_SLICE_PATTERNS:
        for m in pat.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC005", line=lineno,
                message="History returns a DataFrame in Python, not a Slice. "
                        f"Avoid C# patterns like {m.group().strip()}",
                severity="warning", fixed=False,
                original=m.group(), replacement="",
            ))
    return code


# ---------------------------------------------------------------------------
# QC006 — self.history() inside on_data() (warning only)
# ---------------------------------------------------------------------------

def _rule_qc006(code: str, issues: List[LintIssue]) -> str:
    """Warn about expensive history() calls inside on_data()."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != "on_data":
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if (isinstance(func, ast.Attribute) and func.attr == "history"
                        and isinstance(func.value, ast.Name) and func.value.id == "self"):
                    issues.append(LintIssue(
                        rule_id="QC006", line=child.lineno,
                        message="self.history() inside on_data() is expensive — "
                                "consider caching or using scheduled events",
                        severity="warning", fixed=False,
                        original="self.history(...)", replacement="",
                    ))
    return code


# ---------------------------------------------------------------------------
# QC008 — Indicator name shadowing (warning only)
# ---------------------------------------------------------------------------

_INDICATOR_NAMES = frozenset({
    "sma", "ema", "rsi", "macd", "bb", "atr", "adx", "mom", "roc",
    "momp", "std", "aroon", "cci", "stoch", "williams", "obv", "vwap",
    "keltner", "donchian", "ichimoku", "t3", "trix", "dema", "tema",
})


# ---------------------------------------------------------------------------
# QC009 — Wrong asset class API (e.g. add_equity for forex pairs)
# ---------------------------------------------------------------------------

# ISO 4217 major currency codes used in forex pairs
_FOREX_CURRENCIES = frozenset({
    "EUR", "USD", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD",
    "SEK", "NOK", "DKK", "SGD", "HKD", "ZAR", "MXN", "TRY",
    "PLN", "CZK", "HUF", "INR", "CNY", "CNH", "KRW", "BRL",
})

# Common crypto base tickers
_CRYPTO_BASES = frozenset({
    "BTC", "ETH", "LTC", "XRP", "BCH", "ADA", "DOT", "LINK",
    "SOL", "AVAX", "DOGE", "SHIB", "MATIC", "UNI", "AAVE",
    "ATOM", "XLM", "ALGO", "FIL", "NEAR",
})

# Matches: self.add_equity("EUR/USD" ...) or self.add_equity("EURUSD" ...)
# Captures the full call including open paren, quote char, ticker, and quote char
_ADD_EQUITY_TICKER = re.compile(
    r'(self\.add_equity\s*\(\s*)(["\'])([A-Z]{3,10}(?:/[A-Z]{2,5})?)\2'
)


def _is_forex_pair(ticker: str) -> bool:
    """Check if ticker looks like a forex pair (e.g. EUR/USD, EURUSD)."""
    if "/" in ticker:
        parts = ticker.split("/")
        return (len(parts) == 2
                and parts[0] in _FOREX_CURRENCIES
                and parts[1] in _FOREX_CURRENCIES)
    # No slash: EURUSD style (6 chars, both halves are currencies)
    if len(ticker) == 6:
        return (ticker[:3] in _FOREX_CURRENCIES
                and ticker[3:] in _FOREX_CURRENCIES)
    return False


def _is_crypto_pair(ticker: str) -> bool:
    """Check if ticker looks like a crypto pair (e.g. BTCUSD, BTC/USD)."""
    if "/" in ticker:
        base = ticker.split("/")[0]
    elif len(ticker) >= 6:
        base = ticker[:-3]  # assume 3-char quote (USD, EUR, etc.)
    else:
        return False
    return base in _CRYPTO_BASES


def _classify_tickers(tickers: list) -> str:
    """Classify a list of tickers: 'forex', 'crypto', or 'equity'."""
    forex_count = sum(1 for t in tickers if _is_forex_pair(t))
    crypto_count = sum(1 for t in tickers if _is_crypto_pair(t))
    if forex_count > len(tickers) // 2:
        return "forex"
    if crypto_count > len(tickers) // 2:
        return "crypto"
    return "equity"


# Pattern: var = ["EURUSD", "GBPJPY", ...] (list of string literals)
_TICKER_LIST = re.compile(
    r'(\w+)\s*=\s*\[((?:\s*["\'][A-Z]{3,10}(?:/[A-Z]{2,5})?["\']\s*,?\s*)+)\]'
)

# Pattern: for var in list_var: ... self.add_equity(var
_LOOP_ADD_EQUITY = re.compile(
    r'for\s+(\w+)\s+in\s+(\w+)\s*:.*?self\.add_equity\s*\(\s*\1\b',
    re.DOTALL,
)


def _rule_qc009(code: str, issues: List[LintIssue]) -> str:
    """Fix add_equity() used with forex or crypto tickers."""

    # --- Pattern 1: direct inline ticker ---
    matches = list(_ADD_EQUITY_TICKER.finditer(code))
    for m in reversed(matches):
        ticker = m.group(3)
        if _is_forex_pair(ticker):
            lineno = code[:m.start()].count('\n') + 1
            old = m.group()
            new = m.group().replace("self.add_equity", "self.add_forex", 1)
            issues.append(LintIssue(
                rule_id="QC009", line=lineno,
                message=f"Forex pair {ticker} should use self.add_forex(), not self.add_equity()",
                severity="error", fixed=True,
                original=old, replacement=new,
            ))
            code = code[:m.start()] + new + code[m.end():]
        elif _is_crypto_pair(ticker):
            lineno = code[:m.start()].count('\n') + 1
            old = m.group()
            new = m.group().replace("self.add_equity", "self.add_crypto", 1)
            issues.append(LintIssue(
                rule_id="QC009", line=lineno,
                message=f"Crypto pair {ticker} should use self.add_crypto(), not self.add_equity()",
                severity="error", fixed=True,
                original=old, replacement=new,
            ))
            code = code[:m.start()] + new + code[m.end():]

    # --- Pattern 2: ticker list variable + loop with add_equity(var) ---
    # Find all ticker list declarations and classify them
    list_vars: dict = {}  # var_name -> asset_class
    for m in _TICKER_LIST.finditer(code):
        var_name = m.group(1)
        raw = m.group(2)
        tickers = re.findall(r'["\']([A-Z]{3,10}(?:/[A-Z]{2,5})?)["\']', raw)
        asset_class = _classify_tickers(tickers)
        if asset_class != "equity":
            list_vars[var_name] = asset_class

    # Find loops that iterate over a classified list and call add_equity
    if list_vars:
        for m in _LOOP_ADD_EQUITY.finditer(code):
            loop_var = m.group(1)
            list_var = m.group(2)
            asset_class = list_vars.get(list_var)
            if not asset_class:
                continue
            replacement = "self.add_forex" if asset_class == "forex" else "self.add_crypto"
            # Replace add_equity with the correct method in this match
            pat = re.compile(r'self\.add_equity(\s*\(\s*' + re.escape(loop_var) + r'\b)')
            for sub_m in pat.finditer(code):
                lineno = code[:sub_m.start()].count('\n') + 1
                issues.append(LintIssue(
                    rule_id="QC009", line=lineno,
                    message=f"Ticker list {list_var} contains {asset_class} pairs — "
                            f"use {replacement}(), not self.add_equity()",
                    severity="error", fixed=True,
                    original=sub_m.group(), replacement=replacement + sub_m.group(1),
                ))
            code = pat.sub(replacement + r'\1', code)

    return code


def _rule_qc008(code: str, issues: List[LintIssue]) -> str:
    """Warn about self.xxx = ... where xxx is a QCAlgorithm indicator method."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                    and target.attr in _INDICATOR_NAMES):
                issues.append(LintIssue(
                    rule_id="QC008", line=node.lineno,
                    message=f"self.{target.attr} = ... shadows QCAlgorithm.{target.attr}() — "
                            f"use self._{target.attr} instead",
                    severity="warning", fixed=False,
                    original=f"self.{target.attr}", replacement=f"self._{target.attr}",
                ))
    return code


# ---------------------------------------------------------------------------
# QC010 — Reserved QCAlgorithm attribute names (auto-fix)
# ---------------------------------------------------------------------------

# C#-backed properties that crash with "error return without exception set"
# when assigned from Python. Common LLM parameter names that collide.
_RESERVED_ATTRS = frozenset({
    "alpha",          # Alpha framework model
    "universe",       # Universe selection model
    "execution",      # Execution model
    "name",           # Algorithm.Name (read-only)
    "risk_management",  # Risk management model
    "portfolio_construction",  # Portfolio construction model
})


def _rule_qc010(code: str, issues: List[LintIssue]) -> str:
    """Rename self.RESERVED = ... assignments and all references to self._RESERVED."""
    for attr in _RESERVED_ATTRS:
        # Check if there's an assignment to self.<attr>
        assign_pat = re.compile(r'self\.' + re.escape(attr) + r'\s*=')
        if not assign_pat.search(code):
            continue

        # Replace ALL occurrences of self.<attr> (assignments + reads)
        # Word boundary after to avoid self.alpha_value → self._alpha_value
        usage_pat = re.compile(r'self\.' + re.escape(attr) + r'(?![a-zA-Z0-9_])')
        for m in usage_pat.finditer(code):
            lineno = code[:m.start()].count('\n') + 1
            issues.append(LintIssue(
                rule_id="QC010", line=lineno,
                message=f"self.{attr} is a reserved QCAlgorithm property — "
                        f"renamed to self._{attr}",
                severity="error", fixed=True,
                original=f"self.{attr}", replacement=f"self._{attr}",
            ))
        code = usage_pat.sub(f"self._{attr}", code)

    return code


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Rule execution order: case normalization first, then structural fixes, then warnings
_RULES = [
    _rule_qc001,   # PascalCase → snake_case (must run first)
    _rule_qc007,   # Resolution casing
    _rule_qc009,   # Wrong asset class API (runs after QC001 normalizes add_equity)
    _rule_qc010,   # Reserved QCAlgorithm attribute names
    _rule_qc004,   # Action() wrapper
    _rule_qc002,   # len() on RollingWindow
    _rule_qc003,   # .Values on RollingWindow
    _rule_qc005,   # History as Slice (warning)
    _rule_qc006,   # history() in on_data() (warning)
    _rule_qc008,   # Indicator shadowing (warning)
]


def lint_qc_code(code: str) -> LintResult:
    """Run all QC lint rules on *code* and return a LintResult.

    Auto-fix rules mutate the code string. After each auto-fix rule, the code
    is re-parsed to confirm it's still valid Python. If a fix breaks syntax the
    loop stops and returns the last known-good state.
    """
    issues: List[LintIssue] = []
    last_good = code

    for rule_fn in _RULES:
        new_code = rule_fn(code, issues)

        # If an auto-fix rule changed the code, verify syntax
        if new_code != code:
            try:
                ast.parse(new_code)
                code = new_code
                last_good = code
            except SyntaxError:
                logger.warning(
                    "Linter rule %s broke syntax — reverting to last good state",
                    rule_fn.__name__,
                )
                # Remove issues added by this rule (they're at the tail)
                issues[:] = [i for i in issues if i.rule_id != rule_fn.__name__]
                code = last_good
                break
        else:
            code = new_code

    fix_count = sum(1 for i in issues if i.fixed)
    warn_count = sum(1 for i in issues if not i.fixed)
    if fix_count or warn_count:
        logger.info(
            "QC linter: %d auto-fixes applied, %d warnings",
            fix_count, warn_count,
        )

    return LintResult(code=code, issues=issues)
