"""LLM handler for interacting with OpenAI API."""

import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMHandler:
    """Handles interactions with the OpenAI API."""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize OpenAI client with new SDK
        api_key = config.api_key or config.load_api_key()
        self.client = OpenAI(api_key=api_key)
        self.model = config.model.model
        self.temperature = config.model.temperature
        self.max_tokens = config.model.max_tokens

    def generate_summary(self, extracted_data: dict[str, list[str]]) -> str | None:
        """
        Generate a summary of the trading strategy and risk management.

        Args:
            extracted_data: Dictionary containing trading_signal and risk_management data

        Returns:
            Summary text or None if generation failed
        """
        self.logger.info("Generating summary using OpenAI")

        trading_signals = "\n".join(extracted_data.get("trading_signal", []))
        risk_management = "\n".join(extracted_data.get("risk_management", []))

        prompt = f"""Provide a clear and concise summary of the following trading strategy and its associated risk management rules. Ensure the explanation is understandable to traders familiar with basic trading concepts and is no longer than 300 words.

        ### Trading Strategy Overview:
        - Core Strategy: Describe the primary trading approach, including any specific indicators, time frames (e.g., 5-minute), and entry/exit rules.
        - Stock Selection: Highlight any stock filters (e.g., liquidity, trading volume thresholds, or price conditions) used to choose which stocks to trade.
        - Trade Signals: Explain how the strategy determines whether to go long or short, including any conditions based on candlestick patterns or breakouts.

        {trading_signals}

        ### Risk Management Rules:
        - Stop Loss: Describe how stop-loss levels are set (e.g., 10% ATR) and explain the position-sizing rules (e.g., 1% of capital at risk per trade).
        - Exit Conditions: Clarify how and when positions are closed (e.g., at the end of the trading day or if certain price targets are hit).
        - Additional Constraints: Mention any leverage limits or other risk controls (e.g., maximum leverage of 4x, focusing on Stocks in Play).

        {risk_management}

        Summarize the details in a practical and structured format.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an algorithmic trading expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            summary = response.choices[0].message.content.strip()
            self.logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            self.logger.error(f"Error during summary generation: {e}")
            return None

    def generate_qc_code(self, summary: str) -> str | None:
        """
        Generate QuantConnect Python code based on strategy summary.

        Args:
            summary: Trading strategy summary text

        Returns:
            Generated Python code or None if generation failed
        """
        self.logger.info("Generating QuantConnect code using OpenAI")

        prompt = f"""
        You are a QuantConnect algorithm developer. Convert the following trading strategy descriptions into a complete, error-free QuantConnect Python algorithm.

        ### Trading Strategy Summary:
        {summary}

        ### Requirements:
        1. **Initialize Method**:
            - Set the start and end dates.
            - Set the initial cash.
            - Define the universe selection logic as described in trading strategy summary.
            - Initialize required indicators as described in summary.
        2. **OnData Method**:
            - Implement buy/sell logic as described in summary.
            - Ensure indicators are updated correctly.
        3. **Risk Management**:
            - Apply position sizing or stop-loss mechanisms as described in summary.
        4. **Ensure Compliance**:
            - Use only QuantConnect's supported indicators and methods.
            - The code must be syntactically correct and free of errors.

        Return ONLY the Python code, without any markdown formatting or explanations.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant specialized in generating QuantConnect algorithms in Python.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
            )

            generated_code = response.choices[0].message.content.strip()

            # Clean up code if it has markdown formatting
            if "```python" in generated_code:
                generated_code = generated_code.split("```python")[1].split("```")[0].strip()
            elif "```" in generated_code:
                generated_code = generated_code.split("```")[1].split("```")[0].strip()

            self.logger.info("QuantConnect code generated successfully")
            return generated_code

        except Exception as e:
            self.logger.error(f"Error during code generation: {e}")
            return None

    def refine_code(self, code: str) -> str | None:
        """
        Ask the LLM to fix syntax errors in the generated code.

        Args:
            code: Code to refine

        Returns:
            Refined code or None if refinement failed
        """
        self.logger.info("Refining generated code using OpenAI")

        prompt = f"""
        The following QuantConnect Python code may have syntax or logical errors. Please fix them and provide the corrected code.
        Return ONLY the corrected Python code, without any markdown formatting or explanations.

        {code}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in QuantConnect Python algorithms.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=0.2,
            )

            corrected_code = response.choices[0].message.content.strip()

            # Clean up code if it has markdown formatting
            if "```python" in corrected_code:
                corrected_code = corrected_code.split("```python")[1].split("```")[0].strip()
            elif "```" in corrected_code:
                corrected_code = corrected_code.split("```")[1].split("```")[0].strip()

            self.logger.info("Code refined successfully")
            return corrected_code

        except Exception as e:
            self.logger.error(f"Error during code refinement: {e}")
            return None

    def chat(self, message: str, context: list[dict] | None = None) -> str | None:
        """
        Have a chat conversation with the LLM.

        Args:
            message: User message
            context: Optional conversation history

        Returns:
            LLM response or None if chat failed
        """
        self.logger.info("Chatting with LLM")

        messages = context or []
        messages.append({"role": "user", "content": message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            self.logger.error(f"Error during chat: {e}")
            return None
