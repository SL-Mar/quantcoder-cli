"""Parallel execution of agents and tools."""

import asyncio
import logging
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Represents an agent task to execute."""
    agent_class: Any
    params: Dict[str, Any]
    task_id: str = None


@dataclass
class ToolTask:
    """Represents a tool task to execute."""
    tool: Any
    params: Dict[str, Any]
    task_id: str = None


class ParallelExecutor:
    """
    Execute agents and tools in parallel for maximum performance.

    Similar to Claude Code's ability to run multiple sub-agents simultaneously.
    """

    def __init__(self, max_workers: int = 5):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_agents_parallel(
        self,
        agent_tasks: List[AgentTask]
    ) -> List[Any]:
        """
        Execute multiple agents in parallel.

        Args:
            agent_tasks: List of AgentTask objects

        Returns:
            List of agent results in same order as input

        Example:
            >>> tasks = [
            ...     AgentTask(UniverseAgent, {"criteria": "S&P 500"}),
            ...     AgentTask(AlphaAgent, {"strategy": "momentum"}),
            ... ]
            >>> results = await executor.execute_agents_parallel(tasks)
        """
        self.logger.info(f"Executing {len(agent_tasks)} agents in parallel")

        # Create async tasks
        tasks = [
            self._run_agent_async(task)
            for task in agent_tasks
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Agent task {i} failed: {result}")

        return results

    async def execute_tools_parallel(
        self,
        tool_tasks: List[ToolTask]
    ) -> List[Any]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_tasks: List of ToolTask objects

        Returns:
            List of tool results

        Example:
            >>> tasks = [
            ...     ToolTask(search_tool, {"query": "momentum"}),
            ...     ToolTask(download_tool, {"article_id": 1}),
            ... ]
            >>> results = await executor.execute_tools_parallel(tasks)
        """
        self.logger.info(f"Executing {len(tool_tasks)} tools in parallel")

        tasks = [
            self._run_tool_async(task)
            for task in tool_tasks
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def execute_with_dependencies(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute tasks with dependency resolution.

        Args:
            tasks: List of task specifications with dependencies

        Example:
            >>> tasks = [
            ...     {
            ...         "id": "universe",
            ...         "type": "agent",
            ...         "agent": UniverseAgent,
            ...         "params": {},
            ...         "depends_on": []
            ...     },
            ...     {
            ...         "id": "alpha",
            ...         "type": "agent",
            ...         "agent": AlphaAgent,
            ...         "params": {},
            ...         "depends_on": []
            ...     },
            ...     {
            ...         "id": "risk",
            ...         "type": "agent",
            ...         "agent": RiskAgent,
            ...         "params": {"alpha": "{alpha}"},  # Reference alpha result
            ...         "depends_on": ["alpha"]
            ...     }
            ... ]
            >>> results = await executor.execute_with_dependencies(tasks)
        """
        self.logger.info("Executing tasks with dependency resolution")

        # Build dependency graph
        task_map = {task["id"]: task for task in tasks}
        results = {}
        executed = set()

        # Topological sort and execute
        while len(executed) < len(tasks):
            # Find tasks ready to execute (all dependencies met)
            ready = [
                task for task in tasks
                if task["id"] not in executed
                and all(dep in executed for dep in task.get("depends_on", []))
            ]

            if not ready:
                raise ValueError("Circular dependency detected")

            # Execute ready tasks in parallel
            self.logger.info(f"Executing {len(ready)} ready tasks")

            if ready[0]["type"] == "agent":
                agent_tasks = [
                    AgentTask(
                        agent_class=task["agent"],
                        params=self._resolve_params(task["params"], results),
                        task_id=task["id"]
                    )
                    for task in ready
                ]
                batch_results = await self.execute_agents_parallel(agent_tasks)
            else:
                tool_tasks = [
                    ToolTask(
                        tool=task["tool"],
                        params=self._resolve_params(task["params"], results),
                        task_id=task["id"]
                    )
                    for task in ready
                ]
                batch_results = await self.execute_tools_parallel(tool_tasks)

            # Store results
            for task, result in zip(ready, batch_results):
                results[task["id"]] = result
                executed.add(task["id"])

        return results

    def _resolve_params(self, params: Dict, results: Dict) -> Dict:
        """Resolve parameter references to previous results."""
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # Reference to previous result
                ref_key = value[1:-1]
                resolved[key] = results.get(ref_key)
            else:
                resolved[key] = value

        return resolved

    async def _run_agent_async(self, task: AgentTask) -> Any:
        """Run single agent asynchronously."""
        loop = asyncio.get_event_loop()

        def run_agent():
            try:
                agent = task.agent_class(**task.params)
                return agent.execute()
            except Exception as e:
                self.logger.error(f"Agent execution failed: {e}")
                raise

        return await loop.run_in_executor(self.executor, run_agent)

    async def _run_tool_async(self, task: ToolTask) -> Any:
        """Run single tool asynchronously."""
        loop = asyncio.get_event_loop()

        def run_tool():
            try:
                return task.tool.execute(**task.params)
            except Exception as e:
                self.logger.error(f"Tool execution failed: {e}")
                raise

        return await loop.run_in_executor(self.executor, run_tool)

    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)
