"""Quant-perspective prompt refinement based on backtest analysis.

This module analyzes backtest results from a quantitative finance perspective
and suggests prompt variations to expand the research field.

Key responsibilities:
  - Analyze performance metrics (Sharpe, drawdown, win rate, etc.)
  - Identify weaknesses from quant perspective
  - Suggest variations: indicators, asset classes, timeframes, risk approaches
  - Generate refined prompts for next iteration
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from quantcoder.pipeline.baseline import StrategyResult


class VariationType(Enum):
    """Types of variations to explore."""
    INDICATOR = "indicator"
    ASSET_CLASS = "asset_class"
    TIMEFRAME = "timeframe"
    RISK_MANAGEMENT = "risk_management"
    ENTRY_EXIT = "entry_exit"
    FACTOR = "factor"
    UNIVERSE = "universe"


@dataclass
class QuantAnalysis:
    """Quantitative analysis of strategy performance."""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggested_variations: List[Tuple[VariationType, str]] = field(default_factory=list)
    priority_focus: str = ""
    exploration_direction: str = ""


class QuantPerspectiveRefiner:
    """Analyzes backtest results and suggests quant-perspective prompt variations.

    This refiner takes a different approach from generic prompt refinement:
    it analyzes performance metrics from a quantitative finance perspective
    and suggests variations that a quant researcher would consider.

    Example variations:
        - Low Sharpe → try momentum/trend indicators
        - High drawdown → tighter stop-losses, position sizing
        - Low win rate → different entry signals, filters
        - High correlation to market → market-neutral strategies
    """

    # Indicator variations by category
    INDICATORS = {
        'momentum': [
            'RSI (Relative Strength Index)',
            'MACD (Moving Average Convergence Divergence)',
            'Stochastic Oscillator',
            'Rate of Change (ROC)',
            'Williams %R',
            'CCI (Commodity Channel Index)',
        ],
        'trend': [
            'SMA crossover (50/200)',
            'EMA crossover (12/26)',
            'Bollinger Bands',
            'Parabolic SAR',
            'ADX (Average Directional Index)',
            'Ichimoku Cloud',
        ],
        'volatility': [
            'ATR (Average True Range)',
            'Bollinger Band Width',
            'VIX-based signals',
            'Historical Volatility',
            'Keltner Channels',
        ],
        'volume': [
            'OBV (On-Balance Volume)',
            'VWAP (Volume Weighted Average Price)',
            'Accumulation/Distribution',
            'Money Flow Index',
            'Volume Profile',
        ],
        'mean_reversion': [
            'Bollinger Band mean reversion',
            'Z-score of price',
            'RSI oversold/overbought',
            'Pairs trading spread',
            'Ornstein-Uhlenbeck process',
        ],
    }

    # Asset class variations
    ASSET_CLASSES = {
        'equities': [
            'S&P 500 stocks',
            'Russell 2000 small caps',
            'Technology sector (QQQ)',
            'Financial sector (XLF)',
            'Healthcare sector (XLV)',
            'International developed (EFA)',
            'Emerging markets (EEM)',
        ],
        'futures': [
            'E-mini S&P 500 (ES)',
            'Crude Oil (CL)',
            'Gold (GC)',
            'Treasury Bonds (ZB)',
            'Euro FX (6E)',
        ],
        'crypto': [
            'Bitcoin (BTC)',
            'Ethereum (ETH)',
            'Crypto index',
        ],
        'forex': [
            'EUR/USD',
            'GBP/USD',
            'USD/JPY',
            'Major currency basket',
        ],
    }

    # Timeframe variations
    TIMEFRAMES = [
        ('Tick', 'tick-level'),
        ('1 Minute', 'high-frequency'),
        ('5 Minutes', 'intraday'),
        ('15 Minutes', 'intraday swing'),
        ('Hourly', 'short-term'),
        ('4 Hours', 'swing trading'),
        ('Daily', 'position trading'),
        ('Weekly', 'trend following'),
    ]

    # Risk management approaches
    RISK_APPROACHES = [
        'Fixed percentage stop-loss (2%)',
        'ATR-based stop-loss (2 ATR)',
        'Trailing stop (10%)',
        'Time-based exit (5 days max)',
        'Volatility-adjusted position sizing',
        'Kelly criterion position sizing',
        'Maximum drawdown circuit breaker',
        'Correlation-based hedging',
        'Options overlay for tail risk',
    ]

    # Factor approaches
    FACTORS = [
        'Value (P/E, P/B ratios)',
        'Momentum (12-month returns)',
        'Quality (ROE, profit margins)',
        'Size (market cap)',
        'Low Volatility',
        'Dividend Yield',
        'Growth (earnings growth)',
        'Multi-factor combination',
    ]

    def __init__(self, history: Optional[List[StrategyResult]] = None):
        """Initialize refiner with optional history of previous results.

        Args:
            history: List of previous strategy results for learning
        """
        self.history = history or []
        self._explored_variations: List[str] = []

    def analyze(self, result: StrategyResult) -> QuantAnalysis:
        """Analyze strategy result from quant perspective.

        Args:
            result: StrategyResult from baseline pipeline

        Returns:
            QuantAnalysis with strengths, weaknesses, and suggested variations
        """
        analysis = QuantAnalysis()

        sharpe = result.sharpe_ratio
        drawdown = abs(result.max_drawdown)
        total_return = result.total_return
        win_rate = result.backtest_metrics.get('win_rate', 0.5)
        profit_factor = result.backtest_metrics.get('profit_factor', 1.0)

        # Analyze strengths
        if sharpe >= 1.5:
            analysis.strengths.append(f"Excellent risk-adjusted returns (Sharpe: {sharpe:.2f})")
        elif sharpe >= 1.0:
            analysis.strengths.append(f"Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
        elif sharpe >= 0.5:
            analysis.strengths.append(f"Acceptable risk-adjusted returns (Sharpe: {sharpe:.2f})")

        if drawdown < 0.1:
            analysis.strengths.append(f"Low drawdown ({drawdown:.1%})")

        if total_return > 0.2:
            analysis.strengths.append(f"Strong absolute returns ({total_return:.1%})")

        if win_rate > 0.55:
            analysis.strengths.append(f"Good win rate ({win_rate:.1%})")

        if profit_factor > 1.5:
            analysis.strengths.append(f"Strong profit factor ({profit_factor:.2f})")

        # Analyze weaknesses and suggest variations
        if sharpe < 0.5:
            analysis.weaknesses.append(f"Poor risk-adjusted returns (Sharpe: {sharpe:.2f})")
            analysis.suggested_variations.extend([
                (VariationType.INDICATOR, "Try momentum indicators (RSI, MACD)"),
                (VariationType.FACTOR, "Consider factor-based approach (momentum, value)"),
            ])
            analysis.priority_focus = "Improve alpha generation"

        if sharpe < 1.0 and sharpe >= 0.5:
            analysis.suggested_variations.append(
                (VariationType.INDICATOR, "Enhance signal with additional confirmation indicators")
            )

        if drawdown > 0.25:
            analysis.weaknesses.append(f"High drawdown ({drawdown:.1%})")
            analysis.suggested_variations.extend([
                (VariationType.RISK_MANAGEMENT, "Implement tighter stop-losses"),
                (VariationType.RISK_MANAGEMENT, "Add volatility-based position sizing"),
                (VariationType.RISK_MANAGEMENT, "Consider maximum drawdown circuit breaker"),
            ])
            if not analysis.priority_focus:
                analysis.priority_focus = "Improve risk management"

        if win_rate < 0.45:
            analysis.weaknesses.append(f"Low win rate ({win_rate:.1%})")
            analysis.suggested_variations.extend([
                (VariationType.ENTRY_EXIT, "Add entry filters (trend confirmation, volume)"),
                (VariationType.INDICATOR, "Try mean reversion signals for higher win rate"),
            ])

        if profit_factor < 1.0:
            analysis.weaknesses.append(f"Negative expectancy (PF: {profit_factor:.2f})")
            analysis.suggested_variations.extend([
                (VariationType.ENTRY_EXIT, "Improve exit timing (trailing stops, profit targets)"),
                (VariationType.INDICATOR, "Consider different market regime filters"),
            ])

        # Suggest exploration based on overall performance
        if result.success:
            analysis.exploration_direction = self._suggest_exploration_direction(result)
        else:
            analysis.exploration_direction = "Fundamental strategy redesign needed"

        return analysis

    def _suggest_exploration_direction(self, result: StrategyResult) -> str:
        """Suggest direction for next exploration based on success."""
        directions = [
            "Try same approach on different asset class",
            "Test on different timeframe",
            "Add complementary factor exposure",
            "Explore different market regimes",
            "Test with different universe selection",
        ]
        return random.choice(directions)

    def suggest_next_prompt(
        self,
        original_query: str,
        result: StrategyResult,
        analysis: Optional[QuantAnalysis] = None
    ) -> str:
        """Generate next prompt variation based on analysis.

        Args:
            original_query: Original search/strategy query
            result: Previous strategy result
            analysis: Optional pre-computed analysis

        Returns:
            New prompt for next iteration
        """
        if analysis is None:
            analysis = self.analyze(result)

        # Build variation based on analysis
        variation_parts = [original_query]

        # Add specific variations based on weaknesses
        if analysis.priority_focus:
            if "alpha" in analysis.priority_focus.lower():
                indicator = self._get_unexplored_indicator()
                variation_parts.append(f"using {indicator}")
            elif "risk" in analysis.priority_focus.lower():
                risk_approach = self._get_unexplored_risk_approach()
                variation_parts.append(f"with {risk_approach}")

        # Add exploration direction
        if analysis.exploration_direction and result.success:
            if "asset class" in analysis.exploration_direction.lower():
                asset = self._get_unexplored_asset_class()
                variation_parts.append(f"applied to {asset}")
            elif "timeframe" in analysis.exploration_direction.lower():
                timeframe = self._get_unexplored_timeframe()
                variation_parts.append(f"on {timeframe[1]} timeframe")
            elif "factor" in analysis.exploration_direction.lower():
                factor = self._get_unexplored_factor()
                variation_parts.append(f"combined with {factor}")

        # If no specific variation, add random exploration
        if len(variation_parts) == 1:
            variation_parts.append(self._get_random_variation())

        prompt = " ".join(variation_parts)
        self._explored_variations.append(prompt)
        return prompt

    def _get_unexplored_indicator(self) -> str:
        """Get an indicator that hasn't been explored yet."""
        all_indicators = []
        for category_indicators in self.INDICATORS.values():
            all_indicators.extend(category_indicators)

        unexplored = [i for i in all_indicators if i not in str(self._explored_variations)]
        return random.choice(unexplored) if unexplored else random.choice(all_indicators)

    def _get_unexplored_asset_class(self) -> str:
        """Get an asset class that hasn't been explored yet."""
        all_assets = []
        for category_assets in self.ASSET_CLASSES.values():
            all_assets.extend(category_assets)

        unexplored = [a for a in all_assets if a not in str(self._explored_variations)]
        return random.choice(unexplored) if unexplored else random.choice(all_assets)

    def _get_unexplored_timeframe(self) -> Tuple[str, str]:
        """Get a timeframe that hasn't been explored yet."""
        unexplored = [t for t in self.TIMEFRAMES if t[0] not in str(self._explored_variations)]
        return random.choice(unexplored) if unexplored else random.choice(self.TIMEFRAMES)

    def _get_unexplored_risk_approach(self) -> str:
        """Get a risk approach that hasn't been explored yet."""
        unexplored = [r for r in self.RISK_APPROACHES if r not in str(self._explored_variations)]
        return random.choice(unexplored) if unexplored else random.choice(self.RISK_APPROACHES)

    def _get_unexplored_factor(self) -> str:
        """Get a factor that hasn't been explored yet."""
        unexplored = [f for f in self.FACTORS if f not in str(self._explored_variations)]
        return random.choice(unexplored) if unexplored else random.choice(self.FACTORS)

    def _get_random_variation(self) -> str:
        """Get a random variation for exploration."""
        variation_type = random.choice(list(VariationType))

        if variation_type == VariationType.INDICATOR:
            return f"using {self._get_unexplored_indicator()}"
        elif variation_type == VariationType.ASSET_CLASS:
            return f"applied to {self._get_unexplored_asset_class()}"
        elif variation_type == VariationType.TIMEFRAME:
            tf = self._get_unexplored_timeframe()
            return f"on {tf[1]} timeframe"
        elif variation_type == VariationType.RISK_MANAGEMENT:
            return f"with {self._get_unexplored_risk_approach()}"
        elif variation_type == VariationType.FACTOR:
            return f"combined with {self._get_unexplored_factor()}"
        else:
            return f"with enhanced entry/exit logic"

    def generate_strategy_context(
        self,
        original_query: str,
        history: List[StrategyResult]
    ) -> str:
        """Generate rich strategy context from history.

        Args:
            original_query: Original strategy query
            history: List of previous results

        Returns:
            Context string for CoordinatorAgent
        """
        if not history:
            return ""

        context_parts = [
            "Previous Strategy Iterations Analysis:",
            "=" * 40,
        ]

        # Summarize what worked
        successful = [r for r in history if r.success and r.sharpe_ratio >= 0.5]
        if successful:
            best = max(successful, key=lambda r: r.sharpe_ratio)
            context_parts.append(
                f"\nBest performing approach (Sharpe: {best.sharpe_ratio:.2f}):\n"
                f"  - Strategy: {best.name}\n"
                f"  - Max Drawdown: {best.max_drawdown:.1%}\n"
                f"  - Total Return: {best.total_return:.1%}"
            )

        # Summarize what didn't work
        failed = [r for r in history if not r.success or r.sharpe_ratio < 0.5]
        if failed:
            context_parts.append(
                f"\nApproaches to avoid (underperformed):\n"
                f"  - {len(failed)} strategies with Sharpe < 0.5"
            )

        # Add learning insights
        avg_sharpe = sum(r.sharpe_ratio for r in history) / len(history) if history else 0
        context_parts.append(
            f"\nAggregate Insights:\n"
            f"  - Average Sharpe across iterations: {avg_sharpe:.2f}\n"
            f"  - Success rate: {len(successful)}/{len(history)}\n"
            f"  - Target: Sharpe > {max(avg_sharpe + 0.2, 0.8):.2f}"
        )

        return "\n".join(context_parts)

    def get_exploration_summary(self) -> Dict:
        """Get summary of exploration so far."""
        return {
            'total_variations_explored': len(self._explored_variations),
            'explored_variations': self._explored_variations[-10:],  # Last 10
        }
