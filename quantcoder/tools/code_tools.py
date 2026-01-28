"""Tools for code generation, validation, and backtesting."""

import ast
import asyncio
from pathlib import Path
from typing import Optional
from .base import Tool, ToolResult


class GenerateCodeTool(Tool):
    """Tool for generating QuantConnect code from article summaries."""

    @property
    def name(self) -> str:
        return "generate_code"

    @property
    def description(self) -> str:
        return "Generate QuantConnect trading algorithm code from article or consolidated summary"

    def execute(
        self,
        summary_id: int,
        max_refine_attempts: int = 6,
        use_summary_store: bool = True
    ) -> ToolResult:
        """
        Generate QuantConnect code from a summary.

        Args:
            summary_id: Summary ID (can be individual article or consolidated)
            max_refine_attempts: Maximum attempts to refine code
            use_summary_store: If True, look up summary from store; if False, treat as article_id (legacy)

        Returns:
            ToolResult with generated code
        """
        from ..core.processor import ArticleProcessor
        from ..core.summary_store import SummaryStore

        self.logger.info(f"Generating code for summary/article {summary_id}")

        try:
            summary_text = None
            is_consolidated = False
            source_info = None

            if use_summary_store:
                # Try to load from summary store first
                store = SummaryStore(self.config.home_dir)
                summary_data = store.get_summary(summary_id)

                if summary_data:
                    is_consolidated = summary_data.get('is_consolidated', False)

                    if is_consolidated:
                        # Consolidated summary
                        summary_text = summary_data.get('merged_description', '')
                        source_info = {
                            "type": "consolidated",
                            "source_articles": summary_data.get('source_article_ids', []),
                            "references": summary_data.get('references', [])
                        }
                        self.logger.info(f"Using consolidated summary #{summary_id} from articles {source_info['source_articles']}")
                    else:
                        # Individual summary from store
                        summary_text = summary_data.get('summary_text', '')
                        source_info = {
                            "type": "individual",
                            "article_id": summary_data.get('article_id'),
                            "title": summary_data.get('title')
                        }

            # Fallback: treat summary_id as article_id (legacy behavior)
            if not summary_text:
                article_id = summary_id
                filepath = Path(self.config.tools.downloads_dir) / f"article_{article_id}.pdf"

                if not filepath.exists():
                    return ToolResult(
                        success=False,
                        error=f"Summary #{summary_id} not found in store, and article_{article_id}.pdf not downloaded."
                    )

                # Process the article directly
                processor = ArticleProcessor(self.config, max_refine_attempts=max_refine_attempts)
                results = processor.extract_structure_and_generate_code(str(filepath))

                summary = results.get("summary")
                code = results.get("code")

                if not code or code == "QuantConnect code could not be generated successfully.":
                    return ToolResult(
                        success=False,
                        error="Failed to generate valid QuantConnect code",
                        data={"summary": summary}
                    )

                # Save code
                code_dir = Path(self.config.tools.generated_code_dir)
                code_dir.mkdir(parents=True, exist_ok=True)

                code_path = code_dir / f"algorithm_{article_id}.py"
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(code)

                return ToolResult(
                    success=True,
                    data={
                        "code": code,
                        "summary": summary,
                        "path": str(code_path),
                        "source": {"type": "article", "article_id": article_id}
                    },
                    message=f"Code generated and saved to {code_path}"
                )

            # Generate code from summary text (individual or consolidated)
            processor = ArticleProcessor(self.config, max_refine_attempts=max_refine_attempts)
            code = processor.generate_code_from_summary(summary_text)

            if not code or code == "QuantConnect code could not be generated successfully.":
                return ToolResult(
                    success=False,
                    error="Failed to generate valid QuantConnect code",
                    data={"summary": summary_text}
                )

            # Save code with appropriate naming
            code_dir = Path(self.config.tools.generated_code_dir)
            code_dir.mkdir(parents=True, exist_ok=True)

            if is_consolidated:
                code_path = code_dir / f"algorithm_consolidated_{summary_id}.py"
            else:
                article_id = source_info.get('article_id', summary_id) if source_info else summary_id
                code_path = code_dir / f"algorithm_{article_id}.py"

            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)

            return ToolResult(
                success=True,
                data={
                    "code": code,
                    "summary": summary_text,
                    "path": str(code_path),
                    "source": source_info,
                    "is_consolidated": is_consolidated
                },
                message=f"Code generated and saved to {code_path}"
            )

        except Exception as e:
            self.logger.error(f"Error generating code: {e}")
            return ToolResult(success=False, error=str(e))


class ValidateCodeTool(Tool):
    """Tool for validating Python code - locally and via QuantConnect."""

    @property
    def name(self) -> str:
        return "validate_code"

    @property
    def description(self) -> str:
        return "Validate Python code syntax locally and compile on QuantConnect"

    def execute(
        self,
        code: str,
        use_quantconnect: bool = True
    ) -> ToolResult:
        """
        Validate Python code locally and optionally on QuantConnect.

        Args:
            code: Python code to validate
            use_quantconnect: If True, also validate on QuantConnect API

        Returns:
            ToolResult with validation status
        """
        self.logger.info("Validating code")

        # Step 1: Local syntax check
        try:
            ast.parse(code)
            self.logger.info("Local syntax check passed")
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Syntax error: {e.msg} at line {e.lineno}",
                data={"line": e.lineno, "offset": e.offset, "stage": "local"}
            )

        # Step 2: QuantConnect validation (if enabled and credentials available)
        if use_quantconnect and self.config.has_quantconnect_credentials():
            try:
                qc_result = self._validate_on_quantconnect(code)
                if not qc_result["valid"]:
                    return ToolResult(
                        success=False,
                        error="QuantConnect compilation failed",
                        data={
                            "stage": "quantconnect",
                            "errors": qc_result.get("errors", []),
                            "warnings": qc_result.get("warnings", [])
                        }
                    )
                return ToolResult(
                    success=True,
                    message="Code validated locally and compiled on QuantConnect",
                    data={
                        "stage": "quantconnect",
                        "project_id": qc_result.get("project_id"),
                        "compile_id": qc_result.get("compile_id"),
                        "warnings": qc_result.get("warnings", [])
                    }
                )
            except Exception as e:
                self.logger.warning(f"QuantConnect validation failed: {e}")
                # Fall back to local-only validation
                return ToolResult(
                    success=True,
                    message="Code is syntactically correct (QuantConnect validation skipped)",
                    data={"stage": "local", "qc_error": str(e)}
                )

        return ToolResult(
            success=True,
            message="Code is syntactically correct"
        )

    def _validate_on_quantconnect(self, code: str) -> dict:
        """Validate code on QuantConnect API."""
        from ..mcp.quantconnect_mcp import QuantConnectMCPClient

        api_key, user_id = self.config.load_quantconnect_credentials()
        client = QuantConnectMCPClient(api_key, user_id)

        # Run async validation in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(client.validate_code(code))
            return result
        finally:
            loop.close()


class BacktestTool(Tool):
    """Tool for backtesting algorithms on QuantConnect."""

    @property
    def name(self) -> str:
        return "backtest"

    @property
    def description(self) -> str:
        return "Run backtest on QuantConnect and get performance metrics"

    def execute(
        self,
        code: Optional[str] = None,
        file_path: Optional[str] = None,
        start_date: str = "2020-01-01",
        end_date: str = "2024-01-01",
        name: Optional[str] = None
    ) -> ToolResult:
        """
        Run a backtest on QuantConnect.

        Args:
            code: Algorithm code (if not using file_path)
            file_path: Path to algorithm file (alternative to code)
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            name: Optional name for the backtest

        Returns:
            ToolResult with backtest statistics
        """
        # Get code from file or parameter
        if file_path:
            path = Path(file_path)
            if not path.exists():
                # Try in generated_code directory
                path = Path(self.config.tools.generated_code_dir) / file_path
            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            with open(path, 'r') as f:
                code = f.read()
            self.logger.info(f"Loaded code from {path}")
        elif not code:
            return ToolResult(
                success=False,
                error="Either 'code' or 'file_path' must be provided"
            )

        # Check credentials
        if not self.config.has_quantconnect_credentials():
            return ToolResult(
                success=False,
                error="QuantConnect credentials not configured. "
                      "Set QUANTCONNECT_API_KEY and QUANTCONNECT_USER_ID in ~/.quantcoder/.env"
            )

        self.logger.info(f"Running backtest from {start_date} to {end_date}")

        try:
            result = self._run_backtest(code, start_date, end_date, name)

            if not result.get("success"):
                return ToolResult(
                    success=False,
                    error=result.get("error", "Backtest failed"),
                    data=result
                )

            # Extract key metrics
            stats = result.get("statistics", {})
            sharpe = result.get("sharpe")
            total_return = result.get("total_return")

            return ToolResult(
                success=True,
                message=f"Backtest completed. Sharpe: {sharpe}, Return: {total_return}",
                data={
                    "backtest_id": result.get("backtest_id"),
                    "sharpe_ratio": sharpe,
                    "total_return": total_return,
                    "statistics": stats,
                    "runtime_statistics": result.get("runtime_statistics", {})
                }
            )

        except Exception as e:
            self.logger.error(f"Backtest error: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )

    def _run_backtest(
        self,
        code: str,
        start_date: str,
        end_date: str,
        name: Optional[str]
    ) -> dict:
        """Run backtest on QuantConnect API."""
        from ..mcp.quantconnect_mcp import QuantConnectMCPClient

        api_key, user_id = self.config.load_quantconnect_credentials()
        client = QuantConnectMCPClient(api_key, user_id)

        # Run async backtest in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                client.backtest(code, start_date, end_date, name=name)
            )
            return result
        finally:
            loop.close()
