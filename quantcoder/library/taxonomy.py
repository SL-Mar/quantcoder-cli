"""Strategy taxonomy for comprehensive library building."""

from dataclasses import dataclass


@dataclass
class StrategyCategory:
    """Configuration for a strategy category."""

    name: str
    queries: list[str]
    min_strategies: int
    priority: str  # "high", "medium", "low"
    description: str


# Complete strategy taxonomy covering major algorithmic trading approaches
STRATEGY_TAXONOMY = {
    "momentum": StrategyCategory(
        name="momentum",
        queries=[
            "momentum trading strategies",
            "trend following algorithms",
            "relative strength trading",
            "price momentum indicators",
            "dual momentum investing",
        ],
        min_strategies=12,
        priority="high",
        description="Strategies that capitalize on price trends and momentum",
    ),
    "mean_reversion": StrategyCategory(
        name="mean_reversion",
        queries=[
            "mean reversion trading",
            "statistical arbitrage",
            "pairs trading strategies",
            "cointegration trading",
            "bollinger band reversion",
        ],
        min_strategies=12,
        priority="high",
        description="Strategies that profit from price returning to mean",
    ),
    "factor_based": StrategyCategory(
        name="factor_based",
        queries=[
            "value factor investing",
            "quality factor trading",
            "multi-factor models",
            "size factor strategies",
            "fama french factors",
        ],
        min_strategies=10,
        priority="high",
        description="Strategies based on fundamental and market factors",
    ),
    "volatility": StrategyCategory(
        name="volatility",
        queries=[
            "volatility arbitrage",
            "VIX trading strategies",
            "implied volatility trading",
            "volatility term structure",
            "gamma scalping",
        ],
        min_strategies=8,
        priority="medium",
        description="Strategies focused on volatility trading and hedging",
    ),
    "ml_based": StrategyCategory(
        name="ml_based",
        queries=[
            "machine learning trading strategies",
            "deep learning for trading",
            "reinforcement learning trading",
            "neural network trading",
            "ensemble methods trading",
        ],
        min_strategies=10,
        priority="high",
        description="Machine learning and AI-based trading strategies",
    ),
    "market_microstructure": StrategyCategory(
        name="market_microstructure",
        queries=[
            "order flow trading",
            "market making strategies",
            "liquidity provision",
            "bid-ask spread trading",
            "volume profile analysis",
        ],
        min_strategies=6,
        priority="medium",
        description="Strategies exploiting market microstructure patterns",
    ),
    "event_driven": StrategyCategory(
        name="event_driven",
        queries=[
            "earnings announcement trading",
            "merger arbitrage",
            "event-driven strategies",
            "corporate action trading",
            "news-based trading",
        ],
        min_strategies=8,
        priority="medium",
        description="Strategies triggered by specific market events",
    ),
    "options": StrategyCategory(
        name="options",
        queries=[
            "options trading strategies",
            "delta neutral trading",
            "iron condor strategies",
            "covered call strategies",
            "protective put strategies",
        ],
        min_strategies=8,
        priority="medium",
        description="Options-based trading strategies",
    ),
    "cross_asset": StrategyCategory(
        name="cross_asset",
        queries=[
            "cross-asset arbitrage",
            "multi-asset strategies",
            "currency carry trade",
            "commodity momentum",
            "asset allocation strategies",
        ],
        min_strategies=6,
        priority="low",
        description="Strategies spanning multiple asset classes",
    ),
    "alternative_data": StrategyCategory(
        name="alternative_data",
        queries=[
            "alternative data trading",
            "sentiment analysis trading",
            "satellite imagery trading",
            "web scraping strategies",
            "social media sentiment",
        ],
        min_strategies=6,
        priority="low",
        description="Strategies using alternative data sources",
    ),
}


def get_total_strategies_needed() -> int:
    """Calculate total strategies needed for complete library."""
    return sum(cat.min_strategies for cat in STRATEGY_TAXONOMY.values())


def get_categories_by_priority(priority: str) -> dict[str, StrategyCategory]:
    """Get all categories with specified priority."""
    return {name: cat for name, cat in STRATEGY_TAXONOMY.items() if cat.priority == priority}


def get_all_queries() -> list[str]:
    """Get all unique queries across all categories."""
    queries = set()
    for cat in STRATEGY_TAXONOMY.values():
        queries.update(cat.queries)
    return sorted(queries)


def estimate_time_hours(strategies_per_hour: float = 2.0, parallel_factor: float = 3.0) -> float:
    """Estimate time to build complete library."""
    total = get_total_strategies_needed()
    sequential_hours = total / strategies_per_hour
    parallel_hours = sequential_hours / parallel_factor
    return parallel_hours
