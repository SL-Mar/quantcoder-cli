"""Base agent class for all specialized agents."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from ..llm import LLMProvider


@dataclass
class AgentResult:
    """Result from an agent execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    code: Optional[str] = None
    filename: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return self.message or f"Success: {self.data}"
        else:
            return self.error or "Unknown error"


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    def __init__(self, llm: LLMProvider, config: Any = None):
        """
        Initialize agent.

        Args:
            llm: LLM provider instance
            config: Optional configuration object
        """
        self.llm = llm
        self.config = config
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent identifier."""
        pass

    @property
    @abstractmethod
    def agent_description(self) -> str:
        """Agent description."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> AgentResult:
        """
        Execute agent task.

        Returns:
            AgentResult with generated code/data
        """
        pass

    async def _generate_with_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 3000
    ) -> str:
        """
        Generate response using LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User request
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            self.logger.error(f"LLM generation error: {e}")
            raise

    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Remove markdown code blocks
        if "```python" in response:
            parts = response.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
                return code
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                code = parts[1].strip()
                return code

        return response.strip()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(llm={self.llm.get_model_name()})"
