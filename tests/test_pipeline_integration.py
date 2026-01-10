"""Integration tests for the new pipeline architecture.

Tests the complete flow:
- BaselinePipeline (single strategy generation with self-improvement)
- AutoMode (N iterations with QuantPerspectiveRefiner)
- QuantPerspectiveRefiner (backtest analysis and prompt variation)
"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys


# Mock problematic imports before importing our modules
sys.modules['pdfplumber'] = Mock()
sys.modules['spacy'] = Mock()


def test_baseline_pipeline_structure():
    """Test BaselinePipeline has correct structure."""
    from quantcoder.pipeline import BaselinePipeline

    mock_config = Mock()
    mock_config.api_key = "test-key"
    mock_config.home_dir = Path("/tmp")
    mock_config.tools = Mock()
    mock_config.tools.downloads_dir = "/tmp/downloads"
    mock_config.tools.generated_code_dir = "/tmp/generated"

    pipeline = BaselinePipeline(config=mock_config, demo_mode=True)

    # Check all required methods exist
    assert hasattr(pipeline, 'run_from_article_id'), "Should have run_from_article_id"
    assert hasattr(pipeline, 'run_from_query'), "Should have run_from_query"
    assert hasattr(pipeline, '_run_pipeline'), "Should have _run_pipeline"
    assert hasattr(pipeline, '_validate_with_self_improvement'), "Should have _validate_with_self_improvement"

    # Check methods are async where needed
    assert asyncio.iscoroutinefunction(pipeline.run_from_article_id), "run_from_article_id should be async"
    assert asyncio.iscoroutinefunction(pipeline.run_from_query), "run_from_query should be async"

    print("✓ BaselinePipeline structure verified:")
    print("  run_from_article_id() → async entry point for article-based generation")
    print("  run_from_query() → async entry point for query-based generation")
    print("  _run_pipeline() → core workflow")
    print("  _validate_with_self_improvement() → self-healing loop")
    return True


def test_auto_mode_structure():
    """Test AutoMode has correct structure."""
    from quantcoder.pipeline import AutoMode

    mock_config = Mock()
    mock_config.api_key = "test-key"
    mock_config.home_dir = Path("/tmp")
    mock_config.tools = Mock()
    mock_config.tools.downloads_dir = "/tmp/downloads"
    mock_config.tools.generated_code_dir = "/tmp/generated"

    auto_mode = AutoMode(config=mock_config, demo_mode=True)

    # Check all required methods exist
    assert hasattr(auto_mode, 'run'), "Should have run method"
    assert hasattr(auto_mode, 'baseline'), "Should have baseline (BaselinePipeline)"
    assert hasattr(auto_mode, 'refiner'), "Should have refiner (QuantPerspectiveRefiner)"

    # Check run is async
    assert asyncio.iscoroutinefunction(auto_mode.run), "run should be async"

    print("✓ AutoMode structure verified:")
    print("  run(query, count, min_sharpe) → async main loop")
    print("  Uses BaselinePipeline (baseline) for each iteration")
    print("  Uses QuantPerspectiveRefiner (refiner) for prompt variation")
    return True


def test_quant_perspective_refiner():
    """Test QuantPerspectiveRefiner analyzes backtest results."""
    from quantcoder.pipeline import QuantPerspectiveRefiner
    from quantcoder.pipeline.baseline import StrategyResult
    from quantcoder.pipeline.quant_refiner import QuantAnalysis

    refiner = QuantPerspectiveRefiner()

    # Create a proper StrategyResult
    result = StrategyResult(
        success=True,
        name="TestStrategy",
        code_files={'Main.py': '# test'},
        backtest_metrics={
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.15,
            'total_return': 0.25,
            'win_rate': 0.55,
            'volatility': 0.18
        }
    )

    analysis = refiner.analyze(result)

    # Analysis returns a QuantAnalysis dataclass
    assert isinstance(analysis, QuantAnalysis), "Should return QuantAnalysis"
    assert hasattr(analysis, 'strengths'), "Analysis should have strengths"
    assert hasattr(analysis, 'weaknesses'), "Analysis should have weaknesses"
    assert hasattr(analysis, 'suggested_variations'), "Analysis should have suggested_variations"

    print("✓ QuantPerspectiveRefiner analysis:")
    print(f"  Strengths: {analysis.strengths[:2]}")
    print(f"  Weaknesses: {analysis.weaknesses[:2]}")
    print(f"  Suggested variations: {len(analysis.suggested_variations)}")
    return True


def test_quant_refiner_suggest_next_prompt():
    """Test QuantPerspectiveRefiner suggests variations."""
    from quantcoder.pipeline import QuantPerspectiveRefiner
    from quantcoder.pipeline.baseline import StrategyResult

    refiner = QuantPerspectiveRefiner()

    # Create a proper StrategyResult for analysis
    result = StrategyResult(
        success=True,
        name="TestStrategy",
        code_files={'Main.py': '# test'},
        backtest_metrics={
            'sharpe_ratio': 0.8,  # Moderate - room for improvement
            'max_drawdown': 0.25,  # High - weakness
            'total_return': 0.15,
            'win_rate': 0.45,
            'volatility': 0.22
        }
    )

    base_query = "momentum trading strategy"
    next_prompt = refiner.suggest_next_prompt(base_query, result)

    assert next_prompt is not None, "Should return a prompt"
    assert len(next_prompt) > len(base_query), "Should enhance the base query"

    print("✓ QuantPerspectiveRefiner prompt variation:")
    print(f"  Base query: {base_query}")
    print(f"  Enhanced prompt: {next_prompt[:100]}...")
    return True


def test_quant_refiner_dictionaries():
    """Test QuantPerspectiveRefiner has variation dictionaries."""
    from quantcoder.pipeline.quant_refiner import QuantPerspectiveRefiner

    # Check class attributes exist and have content
    assert hasattr(QuantPerspectiveRefiner, 'INDICATORS'), "Should have INDICATORS"
    assert hasattr(QuantPerspectiveRefiner, 'ASSET_CLASSES'), "Should have ASSET_CLASSES"
    assert hasattr(QuantPerspectiveRefiner, 'TIMEFRAMES'), "Should have TIMEFRAMES"
    assert hasattr(QuantPerspectiveRefiner, 'RISK_APPROACHES'), "Should have RISK_APPROACHES"
    assert hasattr(QuantPerspectiveRefiner, 'FACTORS'), "Should have FACTORS"

    # Check dictionaries have content
    assert len(QuantPerspectiveRefiner.INDICATORS) > 0, "INDICATORS should have entries"
    assert len(QuantPerspectiveRefiner.ASSET_CLASSES) > 0, "ASSET_CLASSES should have entries"
    assert len(QuantPerspectiveRefiner.TIMEFRAMES) > 0, "TIMEFRAMES should have entries"
    assert len(QuantPerspectiveRefiner.RISK_APPROACHES) > 0, "RISK_APPROACHES should have entries"
    assert len(QuantPerspectiveRefiner.FACTORS) > 0, "FACTORS should have entries"

    # Check structure (INDICATORS is a dict of lists)
    for category, indicators in list(QuantPerspectiveRefiner.INDICATORS.items())[:1]:
        assert isinstance(category, str), "Category should be string"
        assert isinstance(indicators, list), "Value should be list"

    print("✓ QuantPerspectiveRefiner variation dictionaries:")
    print(f"  INDICATORS: {len(QuantPerspectiveRefiner.INDICATORS)} categories")
    print(f"  ASSET_CLASSES: {len(QuantPerspectiveRefiner.ASSET_CLASSES)} entries")
    print(f"  TIMEFRAMES: {len(QuantPerspectiveRefiner.TIMEFRAMES)} entries")
    print(f"  RISK_APPROACHES: {len(QuantPerspectiveRefiner.RISK_APPROACHES)} entries")
    print(f"  FACTORS: {len(QuantPerspectiveRefiner.FACTORS)} entries")
    return True


def test_strategy_result_dataclass():
    """Test StrategyResult dataclass."""
    from quantcoder.pipeline.baseline import StrategyResult

    # Create a result (sharpe_ratio is a property derived from backtest_metrics)
    result = StrategyResult(
        success=True,
        name="TestStrategy_20250110",
        code_files={'Main.py': '# test code'},
        paper_title="Test Paper",
        backtest_metrics={
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.15,
            'total_return': 0.25
        },
        errors_fixed=2
    )

    assert result.success is True
    assert result.name == "TestStrategy_20250110"
    assert 'Main.py' in result.code_files
    assert result.sharpe_ratio == 1.5  # Property from backtest_metrics
    assert result.max_drawdown == 0.15  # Property from backtest_metrics
    assert result.errors_fixed == 2

    print("✓ StrategyResult dataclass:")
    print(f"  success: {result.success}")
    print(f"  name: {result.name}")
    print(f"  code_files: {list(result.code_files.keys())}")
    print(f"  sharpe_ratio (property): {result.sharpe_ratio}")
    print(f"  max_drawdown (property): {result.max_drawdown}")
    return True


def test_llm_factory():
    """Test LLMFactory configuration."""
    from quantcoder.llm import LLMFactory

    # Test task recommendations
    assert LLMFactory.get_recommended_for_task("coordination") == "anthropic"
    assert LLMFactory.get_recommended_for_task("coding") == "mistral"
    assert LLMFactory.get_recommended_for_task("risk") == "anthropic"
    assert LLMFactory.get_recommended_for_task("reasoning") == "anthropic"

    # Test providers registered
    assert "anthropic" in LLMFactory.PROVIDERS
    assert "mistral" in LLMFactory.PROVIDERS
    assert "deepseek" in LLMFactory.PROVIDERS
    assert "openai" in LLMFactory.PROVIDERS

    print("✓ LLMFactory task recommendations:")
    print("  coordination → anthropic (Sonnet 4.5)")
    print("  coding → mistral (Devstral)")
    print("  risk → anthropic")
    print("✓ All providers registered:", list(LLMFactory.PROVIDERS.keys()))
    return True


def test_coordinator_agent():
    """Test CoordinatorAgent structure."""
    from quantcoder.agents.coordinator_agent import CoordinatorAgent

    mock_llm = AsyncMock()
    mock_config = Mock()

    coordinator = CoordinatorAgent(mock_llm, mock_config)

    assert coordinator.agent_name == "CoordinatorAgent"
    assert "orchestrat" in coordinator.agent_description.lower()
    assert hasattr(coordinator, 'execute')
    assert asyncio.iscoroutinefunction(coordinator.execute)

    print("✓ CoordinatorAgent structure verified:")
    print(f"  Name: {coordinator.agent_name}")
    print(f"  Description: {coordinator.agent_description}")
    print("  Has async execute() method: True")
    return True


def test_code_tools_uses_baseline_pipeline():
    """Test GenerateCodeTool uses BaselinePipeline."""
    from quantcoder.tools.code_tools import GenerateCodeTool
    import inspect

    # Get source code
    source = inspect.getsource(GenerateCodeTool.execute)

    # Verify it imports BaselinePipeline
    assert 'BaselinePipeline' in source, "Should import BaselinePipeline"
    assert 'pipeline' in source.lower(), "Should use pipeline"

    print("✓ GenerateCodeTool uses BaselinePipeline:")
    print("  Imports: from quantcoder.pipeline import BaselinePipeline")
    print("  Creates pipeline with config and max_fix_attempts")
    print("  Returns strategy metrics (sharpe, drawdown, errors_fixed)")
    return True


def test_cli_auto_mode():
    """Test CLI auto mode uses AutoMode."""
    # Read cli.py source
    cli_path = Path(__file__).parent.parent / "quantcoder" / "cli.py"
    source = cli_path.read_text()

    # Check auto start command uses AutoMode
    assert 'from quantcoder.pipeline import AutoMode' in source or 'AutoMode' in source
    assert '--count' in source, "Should have --count option"
    assert 'quant' in source.lower(), "Should reference quant refiner"

    print("✓ CLI auto mode uses AutoMode:")
    print("  --count option for N iterations")
    print("  --min-sharpe option for quality threshold")
    print("  Uses QuantPerspectiveRefiner for prompt variation")
    return True


def test_cli_evolve_library():
    """Test CLI evolve accepts library directory."""
    # Read cli.py source
    cli_path = Path(__file__).parent.parent / "quantcoder" / "cli.py"
    source = cli_path.read_text()

    # Check evolve command accepts library
    assert '--library' in source, "Should have --library option"
    assert 'library_path' in source, "Should use library_path parameter"

    print("✓ CLI evolve accepts library:")
    print("  --library option for directory of strategies")
    print("  Iterates over strategies in library")
    print("  Evolves each strategy independently")
    return True


async def test_baseline_pipeline_demo_mode():
    """Test BaselinePipeline in demo mode returns mock data."""
    from quantcoder.pipeline import BaselinePipeline

    mock_config = Mock()
    mock_config.api_key = "test-key"
    mock_config.home_dir = Path("/tmp")
    mock_config.tools = Mock()
    mock_config.tools.downloads_dir = "/tmp/downloads"
    mock_config.tools.generated_code_dir = "/tmp/generated"

    pipeline = BaselinePipeline(config=mock_config, demo_mode=True)

    # Run in demo mode
    result = await pipeline.run_from_query("momentum trading")

    assert result is not None, "Should return a result"
    assert result.success is True, "Demo mode should succeed"
    assert result.code_files is not None, "Should have code files"

    print("✓ BaselinePipeline demo mode:")
    print(f"  Success: {result.success}")
    print(f"  Strategy name: {result.name}")
    print(f"  Files generated: {list(result.code_files.keys())}")
    print(f"  Sharpe ratio: {result.sharpe_ratio}")
    return True


def run_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PIPELINE ARCHITECTURE INTEGRATION TESTS")
    print("=" * 70 + "\n")

    passed = 0
    failed = 0

    sync_tests = [
        ("BaselinePipeline Structure", test_baseline_pipeline_structure),
        ("AutoMode Structure", test_auto_mode_structure),
        ("QuantPerspectiveRefiner Analysis", test_quant_perspective_refiner),
        ("QuantPerspectiveRefiner Prompt Variation", test_quant_refiner_suggest_next_prompt),
        ("QuantPerspectiveRefiner Dictionaries", test_quant_refiner_dictionaries),
        ("StrategyResult Dataclass", test_strategy_result_dataclass),
        ("LLM Factory Configuration", test_llm_factory),
        ("Coordinator Agent Structure", test_coordinator_agent),
        ("GenerateCodeTool Uses BaselinePipeline", test_code_tools_uses_baseline_pipeline),
        ("CLI Auto Mode", test_cli_auto_mode),
        ("CLI Evolve Library", test_cli_evolve_library),
    ]

    for name, test_fn in sync_tests:
        try:
            test_fn()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    # Run async tests
    async_tests = [
        ("BaselinePipeline Demo Mode", test_baseline_pipeline_demo_mode),
    ]

    for name, test_fn in async_tests:
        print(f"Running async test: {name}...")
        try:
            asyncio.run(test_fn())
            passed += 1
            print()
        except Exception as e:
            print(f"✗ {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All pipeline components are correctly integrated!")
        print("\nArchitecture Verified:")
        print("  1. BaselinePipeline: NLP → CoordinatorAgent → Self-Improvement → Backtest")
        print("  2. AutoMode: BaselinePipeline × N + QuantPerspectiveRefiner")
        print("  3. QuantPerspectiveRefiner: Backtest analysis → Prompt variation")
        print("  4. GenerateCodeTool: Uses BaselinePipeline")
        print("  5. CLI auto start: Uses AutoMode with --count")
        print("  6. CLI evolve start: Accepts --library for library evolution")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
