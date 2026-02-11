"""Tests for the QC API linter (quantcoder.core.qc_linter)."""

import ast
import pytest
from quantcoder.core.qc_linter import lint_qc_code, LintResult, LintIssue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issues_by_rule(result: LintResult, rule_id: str):
    return [i for i in result.issues if i.rule_id == rule_id]


# ---------------------------------------------------------------------------
# QC001 — PascalCase API
# ---------------------------------------------------------------------------

class TestQC001PascalCase:
    """PascalCase method/attribute/def auto-fix."""

    def test_method_calls_fixed(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self.SetStartDate(2024, 1, 1)\n"
            "        self.SetEndDate(2024, 6, 1)\n"
            "        self.SetCash(100000)\n"
            "        self.AddEquity('SPY', Resolution.MINUTE)\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "self.set_start_date" in result.code
        assert "self.set_end_date" in result.code
        assert "self.set_cash" in result.code
        assert "self.add_equity" in result.code
        assert "self.SetStartDate" not in result.code

    def test_attribute_access_fixed(self):
        code = (
            "if self._rsi.IsReady:\n"
            "    price = data['SPY'].Price\n"
            "    val = self._sma.Current.Value\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert ".is_ready" in result.code
        assert ".price" in result.code
        assert ".value" in result.code
        assert ".IsReady" not in result.code

    def test_def_names_fixed(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def Initialize(self):\n"
            "        pass\n"
            "    def OnData(self, data):\n"
            "        pass\n"
            "    def OnOrderEvent(self, event):\n"
            "        pass\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "def initialize(self)" in result.code
        assert "def on_data(self" in result.code
        assert "def on_order_event(self" in result.code
        assert "def Initialize" not in result.code

    def test_clean_code_unchanged(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self.set_start_date(2024, 1, 1)\n"
            "        self.add_equity('SPY', Resolution.MINUTE)\n"
        )
        result = lint_qc_code(code)
        qc001_issues = _issues_by_rule(result, "QC001")
        assert len(qc001_issues) == 0

    def test_portfolio_invested(self):
        code = "if self.portfolio['SPY'].Invested:\n    pass\n"
        result = lint_qc_code(code)
        assert ".invested" in result.code
        assert ".Invested" not in result.code

    def test_chained_schedule_api_fixed(self):
        code = (
            "self.Schedule.On(self.DateRules.EveryDay(), "
            "self.TimeRules.AfterMarketOpen('SPY', 30), self.rebalance)\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "self.schedule.on(" in result.code
        assert "self.date_rules.every_day()" in result.code
        assert "self.time_rules.after_market_open(" in result.code
        assert "self.Schedule.On" not in result.code
        assert "self.DateRules" not in result.code
        assert "self.TimeRules" not in result.code

    def test_chained_time_rules_variants(self):
        code = (
            "self.Schedule.On(self.DateRules.MonthStart(), "
            "self.TimeRules.BeforeMarketClose('SPY', 5), self.close)\n"
        )
        result = lint_qc_code(code)
        assert "self.date_rules.month_start()" in result.code
        assert "self.time_rules.before_market_close(" in result.code

    def test_chained_every_day_vs_every(self):
        """EveryDay should not partially match Every."""
        code = (
            "a = self.DateRules.EveryDay()\n"
            "b = self.DateRules.Every(DayOfWeek.MONDAY)\n"
        )
        result = lint_qc_code(code)
        assert "self.date_rules.every_day()" in result.code
        assert "self.date_rules.every(DayOfWeek" in result.code

    def test_rolling_window_add_fixed(self):
        code = (
            "self.prices = RollingWindow[float](20)\n"
            "self.prices.Add(data['SPY'].close)\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "self.prices.add(" in result.code
        assert "self.prices.Add(" not in result.code

    def test_clean_schedule_api_unchanged(self):
        code = (
            "self.schedule.on(self.date_rules.every_day(), "
            "self.time_rules.after_market_open('SPY', 30), self.rebalance)\n"
        )
        result = lint_qc_code(code)
        qc001_issues = _issues_by_rule(result, "QC001")
        assert len(qc001_issues) == 0


# ---------------------------------------------------------------------------
# QC002 — len() on RollingWindow
# ---------------------------------------------------------------------------

class TestQC002RollingWindowLen:
    """len(rolling_window) → rolling_window.count."""

    def test_len_fixed(self):
        code = (
            "self.prices = RollingWindow[float](20)\n"
            "if len(self.prices) >= 20:\n"
            "    pass\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "self.prices.count" in result.code
        assert "len(self.prices)" not in result.code

    def test_no_rolling_window_no_change(self):
        code = "x = len(some_list)\n"
        result = lint_qc_code(code)
        qc002_issues = _issues_by_rule(result, "QC002")
        assert len(qc002_issues) == 0
        assert "len(some_list)" in result.code

    def test_multiple_rolling_windows(self):
        code = (
            "self.highs = RollingWindow[float](10)\n"
            "self.lows = RollingWindow[float](10)\n"
            "a = len(self.highs)\n"
            "b = len(self.lows)\n"
        )
        result = lint_qc_code(code)
        assert "self.highs.count" in result.code
        assert "self.lows.count" in result.code


# ---------------------------------------------------------------------------
# QC003 — .Values on RollingWindow
# ---------------------------------------------------------------------------

class TestQC003RollingWindowValues:
    """.Values → list()."""

    def test_values_fixed(self):
        code = (
            "self.window = RollingWindow[float](20)\n"
            "vals = self.window.Values\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "list(self.window)" in result.code
        assert ".Values" not in result.code

    def test_no_rolling_window_no_change(self):
        code = "x = some_obj.Values\n"
        result = lint_qc_code(code)
        qc003_issues = _issues_by_rule(result, "QC003")
        assert len(qc003_issues) == 0


# ---------------------------------------------------------------------------
# QC004 — Action() wrapper
# ---------------------------------------------------------------------------

class TestQC004ActionWrapper:
    """Action() removal."""

    def test_action_removed(self):
        code = (
            "self.schedule.on(\n"
            "    self.date_rules.every_day(),\n"
            "    self.time_rules.at(10, 0),\n"
            "    Action(self.rebalance)\n"
            ")\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "self.rebalance" in result.code
        assert "Action(" not in result.code

    def test_no_action_no_change(self):
        code = "self.schedule.on(self.date_rules.every_day(), self.time_rules.at(10, 0), self.rebalance)\n"
        result = lint_qc_code(code)
        qc004_issues = _issues_by_rule(result, "QC004")
        assert len(qc004_issues) == 0


# ---------------------------------------------------------------------------
# QC005 — History DataFrame treated as Slice (warning)
# ---------------------------------------------------------------------------

class TestQC005HistorySlice:
    """Warn about C# History iteration patterns."""

    def test_foreach_warned(self):
        code = "history.ForEach(lambda x: x)\n"
        result = lint_qc_code(code)
        qc005_issues = _issues_by_rule(result, "QC005")
        assert len(qc005_issues) == 1
        assert qc005_issues[0].severity == "warning"
        assert not qc005_issues[0].fixed

    def test_getvalue_warned(self):
        code = "history.GetValue(symbol)\n"
        result = lint_qc_code(code)
        qc005_issues = _issues_by_rule(result, "QC005")
        assert len(qc005_issues) == 1

    def test_bars_access_not_warned(self):
        """data.Bars[symbol] is valid Slice access in on_data, not a History issue."""
        code = "if data.Bars.ContainsKey(self.symbol):\n    price = data.Bars[self.symbol].close\n"
        result = lint_qc_code(code)
        qc005_issues = _issues_by_rule(result, "QC005")
        assert len(qc005_issues) == 0

    def test_clean_history_no_warning(self):
        code = "df = self.history(self.symbol, 20, Resolution.DAILY)\n"
        result = lint_qc_code(code)
        qc005_issues = _issues_by_rule(result, "QC005")
        assert len(qc005_issues) == 0


# ---------------------------------------------------------------------------
# QC006 — history() inside on_data() (warning)
# ---------------------------------------------------------------------------

class TestQC006HistoryInOnData:
    """Warn about expensive history() in on_data()."""

    def test_history_in_on_data_warned(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def on_data(self, data):\n"
            "        df = self.history(self.spy, 20, Resolution.DAILY)\n"
        )
        result = lint_qc_code(code)
        qc006_issues = _issues_by_rule(result, "QC006")
        assert len(qc006_issues) == 1
        assert qc006_issues[0].severity == "warning"

    def test_history_outside_on_data_ok(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        df = self.history(self.spy, 20, Resolution.DAILY)\n"
        )
        result = lint_qc_code(code)
        qc006_issues = _issues_by_rule(result, "QC006")
        assert len(qc006_issues) == 0


# ---------------------------------------------------------------------------
# QC007 — Resolution casing
# ---------------------------------------------------------------------------

class TestQC007ResolutionCasing:
    """Resolution.Daily → Resolution.DAILY etc."""

    def test_resolution_fixed(self):
        code = (
            "self.add_equity('SPY', Resolution.Daily)\n"
            "self.add_equity('QQQ', Resolution.Minute)\n"
            "self.add_equity('IWM', Resolution.Hour)\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes
        assert "Resolution.DAILY" in result.code
        assert "Resolution.MINUTE" in result.code
        assert "Resolution.HOUR" in result.code
        assert "Resolution.Daily" not in result.code

    def test_correct_resolution_unchanged(self):
        code = "self.add_equity('SPY', Resolution.DAILY)\n"
        result = lint_qc_code(code)
        qc007_issues = _issues_by_rule(result, "QC007")
        assert len(qc007_issues) == 0


# ---------------------------------------------------------------------------
# QC008 — Indicator name shadowing (warning)
# ---------------------------------------------------------------------------

class TestQC008IndicatorShadowing:
    """self.rsi = ... shadows QCAlgorithm.rsi()."""

    def test_shadowing_warned(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self.rsi = self.rsi('SPY', 14)\n"
        )
        result = lint_qc_code(code)
        qc008_issues = _issues_by_rule(result, "QC008")
        assert len(qc008_issues) == 1
        assert "self._rsi" in qc008_issues[0].replacement

    def test_prefixed_name_no_warning(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self._rsi = self.rsi('SPY', 14)\n"
        )
        result = lint_qc_code(code)
        qc008_issues = _issues_by_rule(result, "QC008")
        assert len(qc008_issues) == 0

    def test_multiple_indicators_warned(self):
        code = (
            "class MyAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self.sma = self.sma('SPY', 20)\n"
            "        self.ema = self.ema('SPY', 10)\n"
            "        self.macd = self.macd('SPY', 12, 26, 9)\n"
        )
        result = lint_qc_code(code)
        qc008_issues = _issues_by_rule(result, "QC008")
        assert len(qc008_issues) == 3


# ---------------------------------------------------------------------------
# Integration / composition tests
# ---------------------------------------------------------------------------

class TestComposition:
    """Multiple rules apply to the same code."""

    def test_full_pascal_algo(self):
        """Realistic LLM-generated code with multiple issues."""
        code = (
            "from AlgorithmImports import *\n"
            "\n"
            "class MomentumAlgo(QCAlgorithm):\n"
            "    def Initialize(self):\n"
            "        self.SetStartDate(2024, 1, 1)\n"
            "        self.SetEndDate(2024, 6, 1)\n"
            "        self.SetCash(100000)\n"
            "        spy = self.AddEquity('SPY', Resolution.Daily)\n"
            "        self.spy = spy.Symbol\n"
            "        self.rsi = self.RSI(self.spy, 14, Resolution.Daily)\n"
            "        self.prices = RollingWindow[float](20)\n"
            "        self.Schedule.On(\n"
            "            self.DateRules.EveryDay(),\n"
            "            self.TimeRules.AfterMarketOpen('SPY', 30),\n"
            "            Action(self.trade)\n"
            "        )\n"
            "\n"
            "    def OnData(self, data):\n"
            "        if self.rsi.IsReady:\n"
            "            self.prices.Add(data['SPY'].close)\n"
            "            if len(self.prices) >= 20:\n"
            "                avg = sum(self.prices.Values) / 20\n"
            "\n"
            "    def trade(self):\n"
            "        if self.Portfolio['SPY'].Invested:\n"
            "            self.Liquidate()\n"
        )
        result = lint_qc_code(code)
        assert result.had_fixes

        # QC001 fixes
        assert "def initialize(self)" in result.code
        assert "self.set_start_date" in result.code
        assert "self.add_equity" in result.code
        assert "def on_data(self" in result.code
        assert ".invested" in result.code
        assert "self.liquidate" in result.code

        # QC001 chained API fixes
        assert "self.schedule.on(" in result.code
        assert "self.date_rules.every_day()" in result.code
        assert "self.time_rules.after_market_open(" in result.code
        assert "self.Schedule.On" not in result.code

        # QC001 .Add() fix
        assert "self.prices.add(" in result.code
        assert "self.prices.Add(" not in result.code

        # QC007 fixes
        assert "Resolution.DAILY" in result.code
        assert "Resolution.Daily" not in result.code

        # QC004 fix
        assert "Action(" not in result.code

        # QC002 fix
        assert "self.prices.count" in result.code

        # QC003 fix
        assert "list(self.prices)" in result.code

        # QC008 warning (self.rsi = ...)
        qc008_issues = _issues_by_rule(result, "QC008")
        assert len(qc008_issues) >= 1

        # Code must still parse
        ast.parse(result.code)

    def test_clean_code_returns_no_fixes(self):
        """Clean snake_case code should have zero auto-fixes."""
        code = (
            "from AlgorithmImports import *\n"
            "\n"
            "class CleanAlgo(QCAlgorithm):\n"
            "    def initialize(self):\n"
            "        self.set_start_date(2024, 1, 1)\n"
            "        self.set_end_date(2024, 6, 1)\n"
            "        self.set_cash(100000)\n"
            "        self.add_equity('SPY', Resolution.MINUTE)\n"
            "        self._rsi = self.rsi('SPY', 14)\n"
            "\n"
            "    def on_data(self, data):\n"
            "        if self._rsi.is_ready:\n"
            "            self.log(f'RSI: {self._rsi.current.value}')\n"
        )
        result = lint_qc_code(code)
        assert not result.had_fixes


class TestSafety:
    """Auto-fixes must never break syntax."""

    def test_fix_preserves_syntax(self):
        """After all fixes, code must still parse."""
        code = (
            "class Algo(QCAlgorithm):\n"
            "    def Initialize(self):\n"
            "        self.SetStartDate(2024, 1, 1)\n"
            "        self.SetCash(100000)\n"
            "        self.AddEquity('SPY', Resolution.Daily)\n"
            "        self.sma = self.SMA(self.spy, 20, Resolution.Minute)\n"
            "        self.window = RollingWindow[float](10)\n"
            "        self.schedule.on(\n"
            "            self.date_rules.every_day(),\n"
            "            self.time_rules.at(10, 0),\n"
            "            Action(self.rebalance)\n"
            "        )\n"
            "\n"
            "    def OnData(self, data):\n"
            "        if self.sma.IsReady and len(self.window) > 5:\n"
            "            vals = self.window.Values\n"
        )
        result = lint_qc_code(code)
        # Must always parse
        ast.parse(result.code)

    def test_already_broken_code_returned_as_is(self):
        """If input has a syntax error, linter should return it unchanged."""
        code = "def broken(\n"
        result = lint_qc_code(code)
        assert result.code == code

    def test_empty_code(self):
        """Empty string should not crash."""
        result = lint_qc_code("")
        assert result.code == ""
        assert len(result.issues) == 0


class TestLintResultProperties:
    """Test LintResult convenience properties."""

    def test_had_fixes(self):
        result = LintResult(code="", issues=[
            LintIssue("QC001", 1, "msg", "error", True, "a", "b"),
        ])
        assert result.had_fixes is True

    def test_no_fixes(self):
        result = LintResult(code="", issues=[
            LintIssue("QC005", 1, "msg", "warning", False, "a", ""),
        ])
        assert result.had_fixes is False

    def test_unfixable_count(self):
        result = LintResult(code="", issues=[
            LintIssue("QC001", 1, "msg", "error", True, "a", "b"),
            LintIssue("QC005", 2, "warn1", "warning", False, "a", ""),
            LintIssue("QC006", 3, "warn2", "warning", False, "a", ""),
        ])
        assert result.unfixable_count == 2

    def test_unfixable_hints(self):
        result = LintResult(code="", issues=[
            LintIssue("QC005", 2, "history slice", "warning", False, "a", ""),
        ])
        assert result.unfixable_hints == ["history slice"]
