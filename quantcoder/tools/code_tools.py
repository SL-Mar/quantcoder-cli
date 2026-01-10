"""Tools for code generation and validation."""

import ast
import asyncio
from pathlib import Path
from .base import Tool, ToolResult


class GenerateCodeTool(Tool):
    """Tool for generating QuantConnect code from article summaries.

    Uses the BaselinePipeline which provides:
      - NLP extraction from PDF
      - Multi-agent code generation (CoordinatorAgent)
      - Self-improvement loop (ErrorLearner)
      - MCP validation and backtesting
    """

    @property
    def name(self) -> str:
        return "generate_code"

    @property
    def description(self) -> str:
        return "Generate QuantConnect trading algorithm code from article summary"

    def execute(self, article_id: int, max_refine_attempts: int = 6) -> ToolResult:
        """
        Generate QuantConnect code from an article using full pipeline.

        Args:
            article_id: Article ID from search results (1-indexed)
            max_refine_attempts: Maximum attempts to refine code

        Returns:
            ToolResult with generated code and backtest metrics
        """
        self.logger.info(f"Generating code for article {article_id}")

        try:
            # Check if article exists
            filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

            if not filepath.exists():
                return ToolResult(
                    success=False,
                    error=f"Article not downloaded. Please download article {article_id} first."
                )

            # Use BaselinePipeline for full workflow
            from quantcoder.pipeline import BaselinePipeline

            pipeline = BaselinePipeline(
                config=self.config,
                max_fix_attempts=max_refine_attempts,
                demo_mode=False
            )

            # Run pipeline synchronously (wrap async)
            result = asyncio.run(pipeline.run_from_article_id(article_id))

            if not result.success:
                return ToolResult(
                    success=False,
                    error=result.error_message or "Failed to generate valid QuantConnect code"
                )

            # Save code files
            code_dir = Path(self.config.tools.generated_code_dir)
            code_dir.mkdir(parents=True, exist_ok=True)

            strategy_dir = code_dir / result.name
            strategy_dir.mkdir(parents=True, exist_ok=True)

            # Write all code files
            main_code = ""
            for filename, content in result.code_files.items():
                filepath = strategy_dir / filename
                filepath.write_text(content)
                if filename == "Main.py":
                    main_code = content

            # Also save as single file for backwards compatibility
            single_file = code_dir / f"algorithm_{article_id}.py"
            single_file.write_text(main_code or next(iter(result.code_files.values()), ""))

            return ToolResult(
                success=True,
                data={
                    "code": main_code,
                    "code_files": result.code_files,
                    "strategy_name": result.name,
                    "path": str(strategy_dir),
                    "paper_title": result.paper_title,
                    "backtest_metrics": result.backtest_metrics,
                    "sharpe_ratio": result.sharpe_ratio,
                    "max_drawdown": result.max_drawdown,
                    "errors_fixed": result.errors_fixed
                },
                message=f"Strategy '{result.name}' generated (Sharpe: {result.sharpe_ratio:.2f})"
            )

        except Exception as e:
            self.logger.error(f"Error generating code: {e}")
            return ToolResult(success=False, error=str(e))


class ValidateCodeTool(Tool):
    """Tool for validating Python code syntax."""

    @property
    def name(self) -> str:
        return "validate_code"

    @property
    def description(self) -> str:
        return "Validate Python code for syntax errors"

    def execute(self, code: str) -> ToolResult:
        """
        Validate Python code.

        Args:
            code: Python code to validate

        Returns:
            ToolResult with validation status
        """
        self.logger.info("Validating code")

        try:
            ast.parse(code)
            return ToolResult(
                success=True,
                message="Code is syntactically correct"
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Syntax error: {e.msg} at line {e.lineno}",
                data={"line": e.lineno, "offset": e.offset}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}"
            )
