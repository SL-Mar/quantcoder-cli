"""Dynamic prompt enhancement based on learnings."""

from typing import List, Dict
from quantcoder.autonomous.database import LearningDatabase


class PromptRefiner:
    """Enhances agent prompts with learned patterns."""

    def __init__(self, db: LearningDatabase):
        self.db = db

    def inject_learnings(
        self,
        base_prompt: str,
        strategy_type: str = None,
        max_errors: int = 5,
        max_successes: int = 5
    ) -> str:
        """Enhance base prompt with learned error patterns and success strategies."""
        # Get common errors to avoid
        common_errors = self.db.get_common_error_types(limit=max_errors)

        # Get successful fixes
        successful_fixes = self.db.get_all_successful_fixes(min_confidence=0.7)

        # Get performance stats for this strategy type if provided
        perf_stats = None
        if strategy_type:
            perf_stats = self.db.get_performance_stats(strategy_type)

        # Get top strategies for pattern examples
        top_strategies = self.db.get_top_strategies(limit=3)

        # Build enhancement sections
        enhancements = []

        # Error avoidance section
        if common_errors:
            error_section = self._build_error_section(common_errors, successful_fixes)
            enhancements.append(error_section)

        # Success patterns section
        if top_strategies:
            success_section = self._build_success_section(top_strategies)
            enhancements.append(success_section)

        # Performance insights section
        if perf_stats:
            perf_section = self._build_performance_section(perf_stats, strategy_type)
            enhancements.append(perf_section)

        # Combine everything
        if enhancements:
            enhanced_prompt = f"""{base_prompt}

{'=' * 80}
LEARNED PATTERNS - Apply these learnings to improve code quality:
{'=' * 80}

{chr(10).join(enhancements)}
"""
            return enhanced_prompt

        return base_prompt

    def _build_error_section(
        self,
        common_errors: List[Dict],
        successful_fixes: List[Dict]
    ) -> str:
        """Build error avoidance section."""
        section = "🚫 CRITICAL: Avoid These Common Errors:\n\n"

        for i, error in enumerate(common_errors[:5], 1):
            error_type = error['error_type']
            count = error['count']
            fixed_count = error['fixed_count']
            fix_rate = (fixed_count / count * 100) if count > 0 else 0

            section += f"{i}. {error_type.replace('_', ' ').title()}\n"
            section += f"   Occurrences: {count} | Fix rate: {fix_rate:.0f}%\n"

            # Find relevant fix
            relevant_fix = self._find_fix_for_error(error_type, successful_fixes)
            if relevant_fix:
                section += f"   ✓ Solution: {relevant_fix}\n"

            section += "\n"

        return section

    def _build_success_section(self, top_strategies: List[Dict]) -> str:
        """Build success patterns section."""
        section = "✅ SUCCESS PATTERNS - Use these proven approaches:\n\n"

        # Extract common patterns from top strategies
        patterns = self._extract_common_patterns(top_strategies)

        for i, pattern in enumerate(patterns, 1):
            section += f"{i}. {pattern['description']}\n"
            section += f"   Found in {pattern['count']} top strategies\n"
            if pattern.get('example'):
                section += f"   Example: {pattern['example']}\n"
            section += "\n"

        return section

    def _build_performance_section(
        self,
        perf_stats: Dict,
        strategy_type: str
    ) -> str:
        """Build performance insights section."""
        section = f"📊 PERFORMANCE INSIGHTS for {strategy_type}:\n\n"

        avg_sharpe = perf_stats.get('avg_sharpe', 0)
        max_sharpe = perf_stats.get('max_sharpe', 0)
        count = perf_stats.get('count', 0)

        section += f"Historical Performance:\n"
        section += f"  • Average Sharpe: {avg_sharpe:.2f}\n"
        section += f"  • Best Sharpe: {max_sharpe:.2f}\n"
        section += f"  • Strategies analyzed: {count}\n\n"

        if avg_sharpe >= 1.0:
            section += f"Target: Aim for Sharpe > {avg_sharpe:.2f} (proven achievable)\n"
        else:
            section += f"Target: Aim for Sharpe > 1.0 (improve on historical average)\n"

        return section

    def _find_fix_for_error(
        self,
        error_type: str,
        successful_fixes: List[Dict]
    ) -> str:
        """Find a relevant fix for an error type."""
        # In production, you'd do more sophisticated matching
        for fix in successful_fixes:
            if error_type in fix.get('error_pattern', ''):
                return fix['solution_pattern']

        # Return generic advice based on error type
        generic_fixes = {
            'import_error': 'Ensure all QuantConnect imports are correct (from AlgorithmImports import *)',
            'name_error': 'Define all variables before use, check for typos',
            'attribute_error': 'Verify object has the attribute, check QuantConnect API docs',
            'type_error': 'Check function signatures and argument types',
            'syntax_error': 'Review Python syntax, check indentation and colons',
            'api_error': 'Review QuantConnect API documentation for correct usage',
        }

        return generic_fixes.get(error_type, 'Review code carefully')

    def _extract_common_patterns(self, strategies: List[Dict]) -> List[Dict]:
        """Extract common patterns from successful strategies."""
        patterns = []

        # Pattern 1: Check for risk management
        risk_mgmt_count = sum(
            1 for s in strategies
            if 'risk' in str(s.get('code_files', {})).lower()
        )
        if risk_mgmt_count >= 2:
            patterns.append({
                'description': 'Implement explicit risk management',
                'count': risk_mgmt_count,
                'example': 'Use RiskManagementModel or position sizing logic'
            })

        # Pattern 2: Check for universe selection
        universe_count = sum(
            1 for s in strategies
            if 'universe' in str(s.get('code_files', {})).lower()
        )
        if universe_count >= 2:
            patterns.append({
                'description': 'Use custom universe selection',
                'count': universe_count,
                'example': 'Implement UniverseSelectionModel with filters'
            })

        # Pattern 3: Check for alpha signals
        alpha_count = sum(
            1 for s in strategies
            if 'alpha' in str(s.get('code_files', {})).lower() or
               'insight' in str(s.get('code_files', {})).lower()
        )
        if alpha_count >= 2:
            patterns.append({
                'description': 'Generate clear alpha signals with Insights',
                'count': alpha_count,
                'example': 'Return Insight objects with direction, confidence, period'
            })

        # Pattern 4: Average Sharpe of top strategies
        avg_sharpe = sum(s['sharpe_ratio'] for s in strategies if s.get('sharpe_ratio')) / len(strategies)
        patterns.append({
            'description': f'Top strategies achieve Sharpe ratio > {avg_sharpe:.2f}',
            'count': len(strategies),
            'example': 'Focus on signal quality over complexity'
        })

        # Pattern 5: Low refinement attempts
        avg_refinements = sum(
            s.get('refinement_attempts', 0) for s in strategies
        ) / len(strategies)
        if avg_refinements < 2:
            patterns.append({
                'description': 'Generate clean code on first attempt',
                'count': len(strategies),
                'example': 'Follow QuantConnect patterns, avoid common errors'
            })

        return patterns

    def get_enhanced_prompts_for_agents(
        self,
        strategy_type: str = None
    ) -> Dict[str, str]:
        """Get enhanced prompts for all agent types."""
        base_prompts = {
            'coordinator': """You are the Coordinator Agent responsible for orchestrating
            the multi-agent strategy generation workflow.""",

            'universe': """You are the Universe Agent responsible for generating
            Universe.py - the stock selection logic.""",

            'alpha': """You are the Alpha Agent responsible for generating
            Alpha.py - the trading signal generation logic.""",

            'risk': """You are the Risk Agent responsible for generating
            Risk.py - the risk management and position sizing logic.""",

            'strategy': """You are the Strategy Agent responsible for generating
            Main.py - the main algorithm that integrates all components.""",
        }

        enhanced = {}
        for agent_type, base_prompt in base_prompts.items():
            enhanced[agent_type] = self.inject_learnings(
                base_prompt,
                strategy_type=strategy_type
            )

        return enhanced
