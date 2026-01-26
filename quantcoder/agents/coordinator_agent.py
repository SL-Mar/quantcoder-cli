"""Coordinator Agent - Orchestrates multi-agent workflow."""

from typing import Any

from ..execution import ParallelExecutor
from ..llm import LLMFactory
from .alpha_agent import AlphaAgent
from .base import AgentResult, BaseAgent
from .risk_agent import RiskAgent
from .strategy_agent import StrategyAgent
from .universe_agent import UniverseAgent


class CoordinatorAgent(BaseAgent):
    """
    Main coordinator agent that orchestrates the entire workflow.

    Responsibilities:
    - Analyze user request
    - Determine required components
    - Plan execution order
    - Spawn specialized agents (in parallel when possible)
    - Integrate results
    - Validate via MCP
    - Handle errors and refinement
    """

    @property
    def agent_name(self) -> str:
        return "CoordinatorAgent"

    @property
    def agent_description(self) -> str:
        return "Orchestrates multi-agent workflow for algorithm generation"

    async def execute(
        self, user_request: str, strategy_summary: str = "", mcp_client: Any = None
    ) -> AgentResult:
        """
        Coordinate full algorithm generation.

        Args:
            user_request: User's natural language request
            strategy_summary: Optional strategy summary from paper
            mcp_client: Optional QuantConnect MCP client for validation

        Returns:
            AgentResult with all generated files
        """
        self.logger.info(f"Coordinating workflow for: {user_request}")

        try:
            # Step 1: Analyze request and create plan
            plan = await self._create_execution_plan(user_request, strategy_summary)

            self.logger.info(f"Execution plan: {plan}")

            # Step 2: Execute agents according to plan
            results = await self._execute_plan(plan)

            # Step 3: Validate if MCP client available
            if mcp_client:
                results = await self._validate_and_refine(results, mcp_client)

            # Step 4: Package results
            return AgentResult(
                success=True,
                data=results,
                message=f"Generated {len(results.get('files', {}))} files",
                code=results.get("files", {}).get("Main.py", ""),
            )

        except Exception as e:
            self.logger.error(f"Coordination error: {e}")
            return AgentResult(success=False, error=str(e))

    async def _create_execution_plan(
        self, user_request: str, strategy_summary: str
    ) -> dict[str, Any]:
        """
        Analyze request and create execution plan.

        Returns:
            Plan dict with components, parameters, and execution order
        """
        system_prompt = """You are a strategic planning agent for QuantConnect algorithm generation.

Analyze the user's request and determine:
1. Required components (Universe, Alpha, Risk, Main)
2. Execution order and parallelization opportunities
3. Key parameters to extract

Return a JSON plan with:
{
  "components": {
    "universe": "description of universe requirements",
    "alpha": "description of alpha/signals",
    "risk": "description of risk management"
  },
  "parameters": {
    "start_date": "2020-01-01",
    "end_date": "2023-12-31",
    "initial_cash": 100000,
    "risk_per_trade": 0.02
  },
  "execution_strategy": "parallel" or "sequential"
}"""

        user_prompt = f"""Analyze this request and create an execution plan:

User Request: {user_request}

{f"Strategy Summary: {strategy_summary}" if strategy_summary else ""}

Create a plan for generating the QuantConnect algorithm."""

        response = await self._generate_with_llm(
            system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.3
        )

        # Parse JSON plan
        import json

        try:
            plan = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            # Fallback to default plan
            plan = {
                "components": {
                    "universe": user_request,
                    "alpha": user_request,
                    "risk": "2% per trade, max 10 positions",
                },
                "parameters": {
                    "start_date": "2020-01-01",
                    "end_date": "2023-12-31",
                    "initial_cash": 100000,
                },
                "execution_strategy": "parallel",
            }

        return plan

    async def _execute_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the plan by spawning specialized agents.

        Returns:
            Dict with all generated files and metadata
        """
        components = plan.get("components", {})
        parameters = plan.get("parameters", {})
        strategy = plan.get("execution_strategy", "parallel")

        # Create specialized LLMs for different tasks
        code_llm = LLMFactory.create(
            LLMFactory.get_recommended_for_task("coding"),
            self.config.api_key if self.config else "",
        )

        risk_llm = LLMFactory.create(
            LLMFactory.get_recommended_for_task("risk"), self.config.api_key if self.config else ""
        )

        files = {}

        if strategy == "parallel":
            # Execute Universe and Alpha in parallel
            executor = ParallelExecutor()

            from ..execution.parallel_executor import AgentTask

            parallel_tasks = []

            if "universe" in components:
                parallel_tasks.append(
                    AgentTask(
                        agent_class=lambda: UniverseAgent(code_llm, self.config),
                        params={"criteria": components["universe"]},
                        task_id="universe",
                    )
                )

            if "alpha" in components:
                parallel_tasks.append(
                    AgentTask(
                        agent_class=lambda: AlphaAgent(code_llm, self.config),
                        params={"strategy": components["alpha"]},
                        task_id="alpha",
                    )
                )

            results = await executor.execute_agents_parallel(parallel_tasks)

            # Store results
            for i, _task_id in enumerate(["universe", "alpha"][: len(results)]):
                if results[i].success:
                    files[results[i].filename] = results[i].code

            # Execute Risk (may depend on Alpha output)
            if "risk" in components:
                risk_agent = RiskAgent(risk_llm, self.config)
                risk_result = await risk_agent.execute(
                    risk_parameters=components["risk"], alpha_info=components.get("alpha", "")
                )
                if risk_result.success:
                    files[risk_result.filename] = risk_result.code

        else:
            # Sequential execution
            if "universe" in components:
                universe_agent = UniverseAgent(code_llm, self.config)
                result = await universe_agent.execute(criteria=components["universe"])
                if result.success:
                    files[result.filename] = result.code

            if "alpha" in components:
                alpha_agent = AlphaAgent(code_llm, self.config)
                result = await alpha_agent.execute(strategy=components["alpha"])
                if result.success:
                    files[result.filename] = result.code

            if "risk" in components:
                risk_agent = RiskAgent(risk_llm, self.config)
                result = await risk_agent.execute(risk_parameters=components["risk"])
                if result.success:
                    files[result.filename] = result.code

        # Always generate Main.py last (integrates all components)
        strategy_agent = StrategyAgent(self.llm, self.config)
        main_result = await strategy_agent.execute(
            strategy_name="Generated Strategy", components=components, parameters=parameters
        )

        if main_result.success:
            files[main_result.filename] = main_result.code

        return {"files": files, "plan": plan, "components": components}

    async def _validate_and_refine(
        self, results: dict[str, Any], mcp_client: Any, max_attempts: int = 3
    ) -> dict[str, Any]:
        """
        Validate generated code via MCP and refine if needed.

        Args:
            results: Generated files
            mcp_client: QuantConnect MCP client
            max_attempts: Maximum refinement attempts

        Returns:
            Validated and potentially refined results
        """
        files = results.get("files", {})
        main_code = files.get("Main.py", "")

        if not main_code:
            return results

        self.logger.info("Validating code via MCP")

        for attempt in range(max_attempts):
            # Validate
            validation = await mcp_client.validate_code(
                code=main_code, files={k: v for k, v in files.items() if k != "Main.py"}
            )

            if validation.get("valid"):
                self.logger.info("Code validation successful")
                results["validation"] = validation
                return results

            # Refinement needed
            self.logger.warning(f"Validation failed (attempt {attempt + 1}/{max_attempts})")
            errors = validation.get("errors", [])

            # Use LLM to fix errors
            fixed_code = await self._fix_errors(main_code, errors)
            files["Main.py"] = fixed_code
            main_code = fixed_code

        # Max attempts reached
        results["validation"] = validation
        results["validation_warning"] = "Could not fully validate after max attempts"

        return results

    async def _fix_errors(self, code: str, errors: list[str]) -> str:
        """Use LLM to fix validation errors."""
        system_prompt = """You are a QuantConnect debugging expert.

Fix the errors in the provided code and return the corrected version.

Return ONLY the corrected Python code, no explanations."""

        error_list = "\n".join(f"- {error}" for error in errors)

        user_prompt = f"""Fix these errors in the QuantConnect code:

Errors:
{error_list}

Code:
```python
{code}
```

Return corrected code."""

        response = await self._generate_with_llm(
            system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2
        )

        return self._extract_code(response)
